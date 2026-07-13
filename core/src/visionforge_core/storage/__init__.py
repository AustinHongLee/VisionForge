"""儲存層（ADR-0005）：文件式 SQLite＋內容雜湊 blob＋append-only repositories。"""

from visionforge_core.storage.database import MAX_SCHEMA, Database
from visionforge_core.storage.errors import (
    ConflictError,
    NotAProjectError,
    NotFoundError,
    ProjectSchemaTooNewError,
    StorageError,
)
from visionforge_core.storage.media_store import MediaBlobStore
from visionforge_core.storage.project import Project, create_project, open_project
from visionforge_core.storage.repositories import (
    AnnotationRepository,
    ClaimTeachingContextRepository,
    ConceptRepository,
    CostRepository,
    CoverageRepository,
    DecisionRepository,
    GoldenRepository,
    LabelRepository,
    ManifestRepository,
    MediaAssignmentRepository,
    MediaRepository,
    ReviewEventRepository,
    RunRepository,
    TaskRepository,
)

__all__ = [
    "MAX_SCHEMA",
    "AnnotationRepository",
    "ClaimTeachingContextRepository",
    "ConceptRepository",
    "ConflictError",
    "CostRepository",
    "CoverageRepository",
    "Database",
    "DecisionRepository",
    "GoldenRepository",
    "LabelRepository",
    "ManifestRepository",
    "MediaAssignmentRepository",
    "MediaBlobStore",
    "MediaRepository",
    "NotAProjectError",
    "NotFoundError",
    "Project",
    "ProjectSchemaTooNewError",
    "ReviewEventRepository",
    "RunRepository",
    "TaskRepository",
    "StorageError",
    "create_project",
    "open_project",
]
