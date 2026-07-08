"""批次匯入服務：逐檔呼叫凍結的 import_media，不擴張 core 能力。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from visionforge_core.contracts.media import MediaSource
from visionforge_core.storage.project import Project

from visionforge_app.importer.errors import MediaImportError
from visionforge_app.importer.pipeline import (
    DEFAULT_THUMBNAIL_MAX_EDGE,
    ImportOutcome,
    import_media,
)

SUPPORTED_SUFFIXES: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
)


@dataclass(frozen=True)
class BatchImportFailure:
    path: Path
    error: str
    message: str


@dataclass(frozen=True)
class BatchImportOutcome:
    imported: tuple[ImportOutcome, ...]
    duplicated: tuple[ImportOutcome, ...]
    failed: tuple[BatchImportFailure, ...]

    @property
    def total_seen(self) -> int:
        return len(self.imported) + len(self.duplicated) + len(self.failed)


def import_directory(
    project: Project,
    directory: Path,
    *,
    recursive: bool = True,
    thumbnail_max_edge: int = DEFAULT_THUMBNAIL_MAX_EDGE,
) -> BatchImportOutcome:
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    imported: list[ImportOutcome] = []
    duplicated: list[ImportOutcome] = []
    failed: list[BatchImportFailure] = []

    for path in _candidate_files(directory, recursive=recursive):
        try:
            outcome = import_media(
                project,
                path.read_bytes(),
                MediaSource(kind="file", detail=str(path)),
                thumbnail_max_edge=thumbnail_max_edge,
            )
        except (MediaImportError, OSError) as exc:
            failed.append(
                BatchImportFailure(path=path, error=type(exc).__name__, message=str(exc))
            )
            continue

        if outcome.deduplicated:
            duplicated.append(outcome)
        else:
            imported.append(outcome)

    return BatchImportOutcome(
        imported=tuple(imported),
        duplicated=tuple(duplicated),
        failed=tuple(failed),
    )


def _candidate_files(directory: Path, *, recursive: bool) -> list[Path]:
    paths = directory.rglob("*") if recursive else directory.iterdir()
    return sorted(
        (
            path
            for path in paths
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        ),
        key=lambda path: str(path),
    )
