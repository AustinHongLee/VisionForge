from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from visionforge_app.query import get_media, list_media, thumbnail_path
from visionforge_core.contracts import MediaRecord, MediaSource
from visionforge_core.storage import create_project

BASE = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def project(tmp_path: Path):
    proj = create_project(tmp_path / "project", "media-query-test", "4" * 26)
    try:
        yield proj
    finally:
        proj.close()


def _media(n: int, minutes: int) -> MediaRecord:
    return MediaRecord(
        media_hash=f"{n:064x}",
        width_px=800 + n,
        height_px=600 + n,
        format="png",
        byte_size=1000 + n,
        imported_at=BASE + timedelta(minutes=minutes),
        source=MediaSource(kind="file", detail=f"img-{n}.png"),
        exif_normalized=True,
    )


def test_list_media_pages_recent_records(project) -> None:
    oldest = _media(1, 0)
    newest = _media(2, 10)
    middle = _media(3, 5)
    for record in (oldest, newest, middle):
        project.media.add(record)

    first_page = list_media(project, limit=2, offset=0)
    second_page = list_media(project, limit=2, offset=2)

    assert first_page.items == (newest, middle)
    assert first_page.total == 3
    assert first_page.limit == 2
    assert first_page.offset == 0
    assert first_page.has_more is True
    assert second_page.items == (oldest,)
    assert second_page.total == 3
    assert second_page.has_more is False


def test_get_media_returns_none_when_missing(project) -> None:
    record = _media(1, 0)
    project.media.add(record)

    assert get_media(project, record.media_hash) == record
    assert get_media(project, "f" * 64) is None


def test_thumbnail_path_returns_existing_thumbnail(project) -> None:
    record = _media(1, 0)
    project.media.add(record)
    thumb = project.root / "media" / "thumbs" / f"{record.media_hash}.jpg"

    assert thumbnail_path(project, record.media_hash) is None
    thumb.write_bytes(b"thumbnail")
    assert thumbnail_path(project, record.media_hash) == thumb


@pytest.mark.parametrize(("limit", "offset"), [(-1, 0), (100, -1)])
def test_list_media_rejects_negative_pagination(project, limit: int, offset: int) -> None:
    with pytest.raises(ValueError):
        list_media(project, limit=limit, offset=offset)


def test_list_media_empty_project(project) -> None:
    page = list_media(project)

    assert page.items == ()
    assert page.total == 0
    assert page.limit == 100
    assert page.offset == 0
    assert page.has_more is False
