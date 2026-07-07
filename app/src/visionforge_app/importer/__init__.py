"""匯入管線公開介面（票-0003）。政策見 ADR-0006。"""

from __future__ import annotations

from visionforge_app.importer.pipeline import (
    DEFAULT_THUMBNAIL_MAX_EDGE,
    ImportOutcome,
    import_media,
)

__all__ = ["DEFAULT_THUMBNAIL_MAX_EDGE", "ImportOutcome", "import_media"]
