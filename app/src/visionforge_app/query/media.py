"""media 查詢服務：只讀消費 core 儲存介面。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from visionforge_core.contracts import MediaRecord
from visionforge_core.storage.errors import NotFoundError
from visionforge_core.storage.project import Project


@dataclass(frozen=True)
class MediaPage:
    items: tuple[MediaRecord, ...]
    total: int
    limit: int
    offset: int
    has_more: bool


def list_media(project: Project, *, limit: int = 100, offset: int = 0) -> MediaPage:
    if limit < 0 or offset < 0:
        raise ValueError("limit 與 offset 不得為負")

    items = tuple(project.media.iter_recent(limit=limit, offset=offset))
    total = project.media.count()
    return MediaPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


def get_media(project: Project, media_hash: str) -> MediaRecord | None:
    try:
        return project.media.get(media_hash)
    except NotFoundError:
        return None


def thumbnail_path(project: Project, media_hash: str) -> Path | None:
    path = project.root / "media" / "thumbs" / f"{media_hash}.jpg"
    return path if path.is_file() else None
