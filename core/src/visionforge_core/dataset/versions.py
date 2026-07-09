"""Dataset 版本快照（ADR-0010 收尾、憲法 D5）：把已審 Label 凍成一份版本清單。

「一個版本＝一份清單，不是一份拷貝」——媒體以內容雜湊定址，版本只記參照。
純 core：不 IO 影像、不 import providers；version_id／時間由呼叫端注入（A5）。
匯出成 YOLO/COCO 檔屬 userland（app），另票。
"""

from __future__ import annotations

from datetime import datetime

from visionforge_core.contracts import (
    DatasetVersionManifest,
    ManifestEntry,
    ProvenanceSummary,
)
from visionforge_core.storage import Project


def _split(media_hash: str, val_every: int) -> str:
    """確定性切分：每 val_every 筆挑 1 進 val，其餘 train（依 media_hash 前綴）。"""
    return "val" if int(media_hash[:8], 16) % val_every == 0 else "train"


def build_version(
    project: Project,
    *,
    version_id: str,
    created_at: datetime,
    val_every: int = 5,
    note: str = "",
) -> DatasetVersionManifest:
    """由全部已審 Label 建並存一個新 Dataset 版本；無 Label 則拒絕（不版本化空集）。"""
    labels = project.labels.iter_all()
    if not labels:
        raise ValueError("沒有已審 Label，無法建立 Dataset 版本")

    by_media: dict[str, list[str]] = {}
    for label in labels:
        by_media.setdefault(label.media_hash, []).append(label.label_id)

    entries = tuple(
        ManifestEntry(
            media_hash=media_hash,
            label_refs=tuple(sorted(ids)),
            split=_split(media_hash, val_every),
        )
        for media_hash, ids in sorted(by_media.items())
    )

    latest = project.manifests.latest()
    version_number = (latest.version_number + 1) if latest is not None else 1
    parent_ref = latest.version_id if latest is not None else None

    manifest = DatasetVersionManifest(
        version_id=version_id,
        version_number=version_number,
        created_at=created_at,
        parent_ref=parent_ref,
        entries=entries,
        provenance=ProvenanceSummary(human=len(labels), machine_assisted=0, imported=0),
        note=note,
    )
    project.manifests.append(manifest)
    return manifest
