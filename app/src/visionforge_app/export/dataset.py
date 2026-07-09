"""YOLO/COCO 資料集匯出（票-0016）。

版本快照由 core 的 build_version 建立；本模組只依該 manifest 轉成開放格式檔案。
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from visionforge_core.contracts import BBox, DatasetVersionManifest, Label, MediaRecord
from visionforge_core.dataset import build_version
from visionforge_core.storage import Project

ExportFormat = Literal["yolo", "coco"]

_EXT: dict[str, str] = {
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
    "bmp": ".bmp",
    "tiff": ".tif",
}


@dataclass(frozen=True)
class ExportOutcome:
    version_id: str
    fmt: ExportFormat
    out_dir: Path
    image_count: int
    label_count: int
    class_names: tuple[str, ...]


def export_dataset(
    project: Project,
    fmt: ExportFormat,
    *,
    version_id: str,
    created_at: datetime,
    out_root: Path | None = None,
) -> ExportOutcome:
    """建立 Dataset 版本快照，並匯出成 YOLO 或 COCO 檔案。"""
    manifest = build_version(project, version_id=version_id, created_at=created_at)
    root = out_root if out_root is not None else project.root / "exports"
    out_dir = root / version_id
    if out_dir.exists():
        raise ValueError(f"匯出目錄已存在：{out_dir}")

    class_ids, class_names = _class_mapping(project)
    if fmt == "yolo":
        image_count, label_count = _write_yolo(project, manifest, out_dir, class_ids, class_names)
    elif fmt == "coco":
        image_count, label_count = _write_coco(project, manifest, out_dir, class_ids, class_names)
    else:
        raise ValueError(f"不支援的匯出格式：{fmt}")

    return ExportOutcome(
        version_id=version_id,
        fmt=fmt,
        out_dir=out_dir,
        image_count=image_count,
        label_count=label_count,
        class_names=class_names,
    )


def _class_mapping(project: Project) -> tuple[dict[str, int], tuple[str, ...]]:
    nodes = project.taxonomy.list()
    return {node.node_id: index for index, node in enumerate(nodes)}, tuple(
        node.raw_text for node in nodes
    )


def _bbox_labels(project: Project, label_refs: tuple[str, ...]) -> list[Label]:
    labels: list[Label] = []
    for label_ref in label_refs:
        label = project.labels.get(label_ref)
        if isinstance(label.final_geometry, BBox):
            labels.append(label)
    return labels


def _class_id(label: Label, class_ids: dict[str, int]) -> int:
    node_id = label.final_concept.taxonomy_node_id
    if node_id is None or node_id not in class_ids:
        raise ValueError(f"Label {label.label_id} 缺少有效 Taxonomy 映射")
    return class_ids[node_id]


def _media_filename(record: MediaRecord) -> str:
    return f"{record.media_hash}{_EXT[record.format]}"


def _copy_image(project: Project, record: MediaRecord, target: Path) -> None:
    blob = project.blobs.find(record.media_hash)
    if blob is None:
        raise ValueError(f"media blob {record.media_hash[:12]} 不存在")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(blob, target)


def _write_yolo(
    project: Project,
    manifest: DatasetVersionManifest,
    out_dir: Path,
    class_ids: dict[str, int],
    class_names: tuple[str, ...],
) -> tuple[int, int]:
    label_count = 0
    for entry in manifest.entries:
        record = project.media.get(entry.media_hash)
        filename = _media_filename(record)
        _copy_image(project, record, out_dir / "images" / entry.split / filename)

        labels = _bbox_labels(project, entry.label_refs)
        label_count += len(labels)
        lines = [_yolo_line(label, class_ids) for label in labels]
        label_path = out_dir / "labels" / entry.split / f"{record.media_hash}.txt"
        label_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")

    _write_yolo_yaml(out_dir, class_names)
    return len(manifest.entries), label_count


def _yolo_line(label: Label, class_ids: dict[str, int]) -> str:
    bbox = label.final_geometry
    if not isinstance(bbox, BBox):
        raise ValueError("YOLO 只支援 bbox Label")
    cx = (bbox.x1 + bbox.x2) / 2
    cy = (bbox.y1 + bbox.y2) / 2
    width = bbox.x2 - bbox.x1
    height = bbox.y2 - bbox.y1
    return f"{_class_id(label, class_ids)} {cx:.6f} {cy:.6f} {width:.6f} {height:.6f}"


def _write_yolo_yaml(out_dir: Path, class_names: tuple[str, ...]) -> None:
    lines = [
        "path: .",
        "train: images/train",
        "val: images/val",
        f"nc: {len(class_names)}",
        "names:",
    ]
    lines.extend(
        f"  {index}: {json.dumps(name, ensure_ascii=False)}"
        for index, name in enumerate(class_names)
    )
    (out_dir / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_coco(
    project: Project,
    manifest: DatasetVersionManifest,
    out_dir: Path,
    class_ids: dict[str, int],
    class_names: tuple[str, ...],
) -> tuple[int, int]:
    images: list[dict] = []
    annotations: list[dict] = []
    annotation_id = 1
    for image_id, entry in enumerate(manifest.entries, start=1):
        record = project.media.get(entry.media_hash)
        filename = _media_filename(record)
        _copy_image(project, record, out_dir / "images" / filename)
        images.append(
            {
                "id": image_id,
                "file_name": filename,
                "width": record.width_px,
                "height": record.height_px,
            }
        )

        for label in _bbox_labels(project, entry.label_refs):
            bbox = label.final_geometry
            if not isinstance(bbox, BBox):
                continue
            x = bbox.x1 * record.width_px
            y = bbox.y1 * record.height_px
            width = (bbox.x2 - bbox.x1) * record.width_px
            height = (bbox.y2 - bbox.y1) * record.height_px
            annotations.append(
                {
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": _class_id(label, class_ids),
                    "bbox": [x, y, width, height],
                    "area": width * height,
                    "iscrowd": 0,
                }
            )
            annotation_id += 1

    payload = {
        "images": images,
        "annotations": annotations,
        "categories": [
            {"id": index, "name": name} for index, name in enumerate(class_names)
        ],
    }
    (out_dir / "annotations.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(images), len(annotations)
