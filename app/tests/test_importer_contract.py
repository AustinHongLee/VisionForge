"""凍結介面守門測試：簽名與例外契約在，Builder 實作前後皆須通過。"""

from __future__ import annotations

import inspect

from visionforge_app.importer import (
    DEFAULT_THUMBNAIL_MAX_EDGE,
    ImportOutcome,
    import_media,
)
from visionforge_app.importer.errors import (
    MediaDecodeError,
    MediaImportError,
    MultiFrameMediaError,
    UnsupportedMediaFormatError,
)


def test_import_media_signature_frozen() -> None:
    sig = inspect.signature(import_media)
    params = list(sig.parameters)
    assert params[:3] == ["project", "data", "source"]
    assert sig.parameters["thumbnail_max_edge"].default == DEFAULT_THUMBNAIL_MAX_EDGE
    assert sig.parameters["thumbnail_max_edge"].kind is inspect.Parameter.KEYWORD_ONLY


def test_import_outcome_fields() -> None:
    assert [f for f in ImportOutcome.__dataclass_fields__] == [
        "media_hash",
        "record",
        "deduplicated",
    ]


def test_error_taxonomy() -> None:
    for exc in (UnsupportedMediaFormatError, MultiFrameMediaError, MediaDecodeError):
        assert issubclass(exc, MediaImportError)
