"""VisionForge 自有的最小 grid detector；PyTorch BSD 基座、無預訓練權重。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image
from visionforge_core.contracts import (
    BBox,
    DatasetItem,
    DatasetVersion,
    EvaluationError,
    EvaluationMetric,
    ModelPrediction,
    TrainingRun,
)
from visionforge_core.storage import Project

GRID_SIZE = 8
SLOTS = 3


class TrainingDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrainResult:
    metrics: tuple[EvaluationMetric, ...]
    errors: tuple[EvaluationError, ...]
    predictions_by_media: dict[str, tuple[ModelPrediction, ...]]


def _torch() -> Any:
    try:
        import torch
    except ImportError as exc:
        raise TrainingDependencyError(
            "尚未安裝本地訓練引擎；請安裝 VisionForge training optional dependency"
        ) from exc
    return torch


def _build_model(class_count: int):
    torch = _torch()
    nn = torch.nn

    class TinyDetector(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.backbone = nn.Sequential(
                nn.Conv2d(3, 16, 3, stride=2, padding=1),
                nn.BatchNorm2d(16),
                nn.SiLU(),
                nn.Conv2d(16, 32, 3, stride=2, padding=1),
                nn.BatchNorm2d(32),
                nn.SiLU(),
                nn.Conv2d(32, 64, 3, stride=2, padding=1),
                nn.BatchNorm2d(64),
                nn.SiLU(),
                nn.Conv2d(64, 96, 3, stride=2, padding=1),
                nn.BatchNorm2d(96),
                nn.SiLU(),
                nn.Conv2d(96, 128, 3, stride=2, padding=1),
                nn.BatchNorm2d(128),
                nn.SiLU(),
                nn.AdaptiveAvgPool2d((GRID_SIZE, GRID_SIZE)),
            )
            self.head = nn.Conv2d(128, SLOTS * (5 + class_count), 1)

        def forward(self, images):
            output = self.head(self.backbone(images))
            batch = output.shape[0]
            return output.reshape(
                batch, SLOTS, 5 + class_count, GRID_SIZE, GRID_SIZE
            ).permute(0, 1, 3, 4, 2)

    return TinyDetector()


def _image_tensor(data: bytes, size: int):
    torch = _torch()
    with Image.open(BytesIO(data)) as source:
        image = source.convert("RGB").resize((size, size), Image.Resampling.BILINEAR)
        raw = bytearray(image.tobytes())
    return (
        torch.tensor(raw, dtype=torch.uint8)
        .reshape(size, size, 3)
        .permute(2, 0, 1)
        .float()
        .div(255)
    )


def _item_target(item: DatasetItem, class_ids: dict[str, int], class_count: int):
    torch = _torch()
    obj = torch.zeros((SLOTS, GRID_SIZE, GRID_SIZE), dtype=torch.float32)
    bbox = torch.zeros((SLOTS, GRID_SIZE, GRID_SIZE, 4), dtype=torch.float32)
    classes = torch.zeros((SLOTS, GRID_SIZE, GRID_SIZE), dtype=torch.long)
    for annotation in item.annotations:
        box = annotation.bbox
        center_x = (box.x1 + box.x2) / 2
        center_y = (box.y1 + box.y2) / 2
        cell_x = min(GRID_SIZE - 1, int(center_x * GRID_SIZE))
        cell_y = min(GRID_SIZE - 1, int(center_y * GRID_SIZE))
        free = next(
            (slot for slot in range(SLOTS) if obj[slot, cell_y, cell_x].item() == 0),
            None,
        )
        if free is None:
            raise ValueError(
                f"圖片 {item.media_hash[:12]} 的同一網格超過 {SLOTS} 個物件；"
                "請提高輸入尺寸或改用較高容量 Trainer"
            )
        obj[free, cell_y, cell_x] = 1
        bbox[free, cell_y, cell_x] = torch.tensor([box.x1, box.y1, box.x2, box.y2])
        class_index = class_ids[annotation.concept_id]
        if class_index >= class_count:
            raise ValueError("Dataset class map 超出 Trainer 輸出")
        classes[free, cell_y, cell_x] = class_index
    return obj, bbox, classes


def _batches(values: list[Any], batch_size: int):
    for offset in range(0, len(values), batch_size):
        yield values[offset : offset + batch_size]


def train_and_evaluate(
    project: Project,
    run: TrainingRun,
    artifact_path: Path,
    *,
    progress: Callable[[int, int, float], None],
) -> TrainResult:
    torch = _torch()
    torch.manual_seed(run.recipe.seed)
    dataset = project.dataset_versions.get(run.dataset_version_id)
    class_ids = {entry.concept_id: entry.class_index for entry in dataset.class_map}
    class_count = len(class_ids)
    model = _build_model(class_count)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=run.recipe.learning_rate, weight_decay=1e-4
    )
    bce = torch.nn.BCEWithLogitsLoss()
    train_items = [item for item in dataset.items if item.split == "train"]
    samples = [
        (
            _image_tensor(_blob(project, item.media_hash), run.recipe.input_size),
            _item_target(item, class_ids, class_count),
        )
        for item in train_items
    ]
    model.train()
    for epoch in range(1, run.recipe.epochs + 1):
        total_loss = 0.0
        for batch in _batches(samples, run.recipe.batch_size):
            images = torch.stack([sample[0] for sample in batch])
            obj_targets = torch.stack([sample[1][0] for sample in batch])
            bbox_targets = torch.stack([sample[1][1] for sample in batch])
            class_targets = torch.stack([sample[1][2] for sample in batch])
            output = model(images)
            obj_logits = output[..., 0]
            positive = obj_targets.bool()
            loss = bce(obj_logits, obj_targets)
            if positive.any():
                predicted_boxes = output[..., 1:5].sigmoid()
                loss = loss + 5 * torch.nn.functional.smooth_l1_loss(
                    predicted_boxes[positive], bbox_targets[positive]
                )
                loss = loss + torch.nn.functional.cross_entropy(
                    output[..., 5:][positive], class_targets[positive]
                )
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach())
        progress(epoch, run.recipe.epochs, total_loss / max(1, len(samples)))

    artifact_path.parent.mkdir(parents=True, exist_ok=False)
    torch.save(
        {
            "class_map": [entry.model_dump(mode="json") for entry in dataset.class_map],
            "grid_size": GRID_SIZE,
            "input_size": run.recipe.input_size,
            "slots": SLOTS,
            "state_dict": model.state_dict(),
            "trainer_id": run.trainer_id,
            "trainer_version": run.trainer_version,
        },
        artifact_path,
    )
    return _evaluate(project, dataset, model, run.recipe.input_size, threshold=0.35)


def load_and_predict(
    artifact_path: Path,
    data: bytes,
    *,
    threshold: float,
) -> tuple[ModelPrediction, ...]:
    torch = _torch()
    payload = torch.load(artifact_path, map_location="cpu", weights_only=True)
    class_map = payload["class_map"]
    model = _build_model(len(class_map))
    model.load_state_dict(payload["state_dict"])
    return _predict(
        model,
        _image_tensor(data, int(payload["input_size"])),
        class_map,
        threshold,
    )


def _predict(model, image, class_map: list[dict], threshold: float):
    torch = _torch()
    model.eval()
    with torch.no_grad():
        output = model(image.unsqueeze(0))[0]
    obj = output[..., 0].sigmoid()
    boxes = output[..., 1:5].sigmoid()
    class_prob, class_index = output[..., 5:].softmax(dim=-1).max(dim=-1)
    candidates: list[ModelPrediction] = []
    for slot, row, column in (obj * class_prob >= threshold).nonzero().tolist():
        box = boxes[slot, row, column].tolist()
        x1, x2 = sorted((max(0.0, min(1.0, box[0])), max(0.0, min(1.0, box[2]))))
        y1, y2 = sorted((max(0.0, min(1.0, box[1])), max(0.0, min(1.0, box[3]))))
        if x2 - x1 < 0.005 or y2 - y1 < 0.005:
            continue
        mapping = class_map[int(class_index[slot, row, column])]
        candidates.append(
            ModelPrediction(
                concept_id=mapping["concept_id"],
                display_name=mapping["display_name"],
                bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                confidence=float(obj[slot, row, column] * class_prob[slot, row, column]),
            )
        )
    return tuple(_nms(candidates, iou_threshold=0.45))


def _nms(predictions: list[ModelPrediction], iou_threshold: float):
    kept: list[ModelPrediction] = []
    for candidate in sorted(predictions, key=lambda item: item.confidence, reverse=True):
        if all(
            candidate.concept_id != previous.concept_id
            or _iou(candidate.bbox, previous.bbox) < iou_threshold
            for previous in kept
        ):
            kept.append(candidate)
    return kept


def _evaluate(
    project: Project,
    dataset: DatasetVersion,
    model,
    input_size: int,
    *,
    threshold: float,
) -> TrainResult:
    class_map = [entry.model_dump(mode="json") for entry in dataset.class_map]
    tp = fp = fn = 0
    matched_ious: list[float] = []
    errors: list[EvaluationError] = []
    predictions_by_media: dict[str, tuple[ModelPrediction, ...]] = {}
    for item in (item for item in dataset.items if item.split == "validation"):
        predictions = _predict(
            model,
            _image_tensor(_blob(project, item.media_hash), input_size),
            class_map,
            threshold,
        )
        predictions_by_media[item.media_hash] = predictions
        unmatched = set(range(len(predictions)))
        for expected in item.annotations:
            same_class = [
                index
                for index in unmatched
                if predictions[index].concept_id == expected.concept_id
            ]
            best = max(
                same_class,
                key=lambda index: _iou(expected.bbox, predictions[index].bbox),
                default=None,
            )
            best_iou = 0.0 if best is None else _iou(expected.bbox, predictions[best].bbox)
            if best is not None and best_iou >= 0.5:
                tp += 1
                matched_ious.append(best_iou)
                unmatched.remove(best)
            else:
                fn += 1
                errors.append(
                    EvaluationError(
                        media_hash=item.media_hash,
                        kind="missed" if best is None else "localization",
                        concept_id=expected.concept_id,
                        expected_bbox=expected.bbox,
                        predicted_bbox=None if best is None else predictions[best].bbox,
                        confidence=None if best is None else predictions[best].confidence,
                    )
                )
        for index in unmatched:
            fp += 1
            prediction = predictions[index]
            errors.append(
                EvaluationError(
                    media_hash=item.media_hash,
                    kind="false_positive",
                    concept_id=prediction.concept_id,
                    predicted_bbox=prediction.bbox,
                    confidence=prediction.confidence,
                )
            )
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    mean_iou = sum(matched_ious) / max(1, len(matched_ious))
    return TrainResult(
        metrics=(
            EvaluationMetric(name="precision", value=precision),
            EvaluationMetric(name="recall", value=recall),
            EvaluationMetric(name="mean_iou", value=mean_iou),
        ),
        errors=tuple(errors[:100]),
        predictions_by_media=predictions_by_media,
    )


def _blob(project: Project, media_hash: str) -> bytes:
    path = project.blobs.find(media_hash)
    if path is None:
        raise ValueError(f"media blob {media_hash[:12]} 不存在")
    return path.read_bytes()


def _iou(left: BBox, right: BBox) -> float:
    x1 = max(left.x1, right.x1)
    y1 = max(left.y1, right.y1)
    x2 = min(left.x2, right.x2)
    y2 = min(left.y2, right.y2)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = (left.x2 - left.x1) * (left.y2 - left.y1)
    right_area = (right.x2 - right.x1) * (right.y2 - right.y1)
    return intersection / max(1e-12, left_area + right_area - intersection)
