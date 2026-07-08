"""MediaRepository.iter_recent 列舉測試（解鎖 media 查詢服務）。"""

from datetime import datetime, timedelta, timezone

from visionforge_core.contracts import MediaRecord, MediaSource
from visionforge_core.storage import create_project

BASE = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


def media(n: int, minutes: int) -> MediaRecord:
    return MediaRecord(
        media_hash=f"{n:064x}", width_px=800, height_px=600, format="png",
        byte_size=1000, imported_at=BASE + timedelta(minutes=minutes),
        source=MediaSource(kind="file", detail=f"img{n}.png"), exif_normalized=True,
    )


def test_iter_recent_orders_by_imported_at_desc(tmp_path):
    proj = create_project(tmp_path / "p", "q", "0" * 26)
    try:
        proj.media.add(media(1, 0))
        proj.media.add(media(2, 10))
        proj.media.add(media(3, 5))
        recent = proj.media.iter_recent(limit=10)
        assert [r.media_hash for r in recent] == [f"{2:064x}", f"{3:064x}", f"{1:064x}"]
        page = proj.media.iter_recent(limit=1, offset=1)
        assert [r.media_hash for r in page] == [f"{3:064x}"]
        assert proj.media.iter_recent(limit=10, offset=99) == []
    finally:
        proj.close()
