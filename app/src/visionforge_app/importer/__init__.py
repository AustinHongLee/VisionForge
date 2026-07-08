"""匯入管線公開介面（票-0003）。政策見 ADR-0006。"""

from __future__ import annotations

from visionforge_app.importer.batch import (
    SUPPORTED_SUFFIXES,
    BatchImportFailure,
    BatchImportOutcome,
    import_directory,
)
from visionforge_app.importer.pipeline import (
    DEFAULT_THUMBNAIL_MAX_EDGE,
    ImportOutcome,
    import_media,
)

__all__ = [
    "DEFAULT_THUMBNAIL_MAX_EDGE",
    "SUPPORTED_SUFFIXES",
    "BatchImportFailure",
    "BatchImportOutcome",
    "ImportOutcome",
    "import_directory",
    "import_media",
]
