"""Standalone CapabilityRelease runner；本檔會原樣放入 Release，不依賴 Studio。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

GRID_SIZE = 8
SLOTS = 3


def _build_model(class_count: int):
    import torch

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


def _image_tensor(path: Path, size: int):
    import torch

    with Image.open(path) as source:
        image = source.convert("RGB").resize((size, size), Image.Resampling.BILINEAR)
        raw = bytearray(image.tobytes())
    return (
        torch.tensor(raw, dtype=torch.uint8)
        .reshape(size, size, 3)
        .permute(2, 0, 1)
        .float()
        .div(255)
    )


def _iou(left: dict, right: dict) -> float:
    x1 = max(left["x1"], right["x1"])
    y1 = max(left["y1"], right["y1"])
    x2 = min(left["x2"], right["x2"])
    y2 = min(left["y2"], right["y2"])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = (left["x2"] - left["x1"]) * (left["y2"] - left["y1"])
    right_area = (right["x2"] - right["x1"]) * (right["y2"] - right["y1"])
    return intersection / max(1e-12, left_area + right_area - intersection)


def _nms(predictions: list[dict], threshold: float = 0.45) -> list[dict]:
    kept: list[dict] = []
    for candidate in sorted(predictions, key=lambda item: item["confidence"], reverse=True):
        if all(
            candidate["concept_id"] != previous["concept_id"]
            or _iou(candidate["bbox"], previous["bbox"]) < threshold
            for previous in kept
        ):
            kept.append(candidate)
    return kept


def predict_release(release_dir: Path, image_path: Path) -> dict:
    import torch

    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    artifact_path = release_dir / manifest["execution"]["artifact_path"]
    if artifact_path.name.endswith(".fixture.json"):
        predictions: list[dict] = []
    else:
        payload = torch.load(artifact_path, map_location="cpu", weights_only=True)
        class_map = payload["class_map"]
        model = _build_model(len(class_map))
        model.load_state_dict(payload["state_dict"])
        model.eval()
        with torch.no_grad():
            output = model(_image_tensor(image_path, int(payload["input_size"])).unsqueeze(0))[0]
        obj = output[..., 0].sigmoid()
        boxes = output[..., 1:5].sigmoid()
        class_prob, class_index = output[..., 5:].softmax(dim=-1).max(dim=-1)
        threshold = float(manifest["execution"]["confidence_threshold"])
        predictions = []
        for slot, row, column in (obj * class_prob >= threshold).nonzero().tolist():
            values = boxes[slot, row, column].tolist()
            x1, x2 = sorted((max(0.0, min(1.0, values[0])), max(0.0, min(1.0, values[2]))))
            y1, y2 = sorted((max(0.0, min(1.0, values[1])), max(0.0, min(1.0, values[3]))))
            if x2 - x1 < 0.005 or y2 - y1 < 0.005:
                continue
            mapping = class_map[int(class_index[slot, row, column])]
            predictions.append(
                {
                    "bbox": {"type": "bbox", "x1": x1, "x2": x2, "y1": y1, "y2": y2},
                    "concept_id": mapping["concept_id"],
                    "confidence": float(obj[slot, row, column] * class_prob[slot, row, column]),
                    "display_name": mapping["display_name"],
                }
            )
        predictions = _nms(predictions)
    return {
        "schema_version": "1.0",
        "release_version": manifest["release"]["version_number"],
        "predictions": predictions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a portable VisionForge CapabilityRelease")
    parser.add_argument("--release", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-parity", action="store_true")
    args = parser.parse_args()
    release_dir = args.release.resolve()
    if args.verify_parity:
        manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
        input_path = release_dir / manifest["parity"]["input"]
    elif args.input is not None:
        input_path = args.input.resolve()
    else:
        parser.error("--input is required unless --verify-parity is used")
    result = predict_release(release_dir, input_path)
    if args.verify_parity:
        expected = json.loads(
            (release_dir / "parity" / "expected.json").read_text(encoding="utf-8")
        )
        if result != expected:
            raise SystemExit("Parity verification failed")
        print("Parity verification passed")
        return
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
