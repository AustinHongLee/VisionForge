"""專案資料夾：自包含、可攜、開放格式（P6/A7）。

一個專案＝一個資料夾：project.json（人類可讀的戶口名簿）＋ project.db（SQLite）
＋ media/blobs（內容雜湊定址檔案）。複製資料夾＝完整備份。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from visionforge_core.storage.database import MAX_SCHEMA, Database
from visionforge_core.storage.errors import NotAProjectError
from visionforge_core.storage.media_store import MediaBlobStore
from visionforge_core.storage.repositories import (
    AnnotationRepository,
    CalibrationRepository,
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
    TaxonomyRepository,
)

MARKER = "project.json"


class Project:
    """單一專案的儲存門面：一條連線、全部 repository、blob 庫。"""

    def __init__(self, root: Path, db: Database) -> None:
        self.root = root
        self.db = db
        self.blobs = MediaBlobStore(root / "media" / "blobs")
        self.media = MediaRepository(db)
        self.tasks = TaskRepository(db)
        self.concepts = ConceptRepository(db)
        self.assignments = MediaAssignmentRepository(db)
        self.coverage = CoverageRepository(db)
        self.annotations = AnnotationRepository(db)
        self.claim_teaching_context = ClaimTeachingContextRepository(db)
        self.runs = RunRepository(db)
        self.labels = LabelRepository(db)
        self.decisions = DecisionRepository(db)
        self.costs = CostRepository(db)
        self.review_events = ReviewEventRepository(db)
        self.manifests = ManifestRepository(db)
        self.golden = GoldenRepository(db)
        self.taxonomy = TaxonomyRepository(db)
        self.calibrations = CalibrationRepository(db)

    def close(self) -> None:
        self.db.close()


def create_project(root: Path, name: str, project_id: str) -> Project:
    if root.exists() and any(root.iterdir()):
        raise NotAProjectError(f"目標資料夾非空，拒絕建立專案：{root}")
    root.mkdir(parents=True, exist_ok=True)
    marker = {
        "visionforge_project": True,
        "project_id": project_id,
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "min_schema": MAX_SCHEMA,
    }
    tmp = root / (MARKER + ".tmp")
    tmp.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, root / MARKER)  # 原子：不存在寫到一半的戶口名簿
    (root / "media" / "thumbs").mkdir(parents=True, exist_ok=True)
    return open_project(root)


def open_project(root: Path) -> Project:
    marker_path = root / MARKER
    if not marker_path.is_file():
        raise NotAProjectError(f"{root} 不是 VisionForge 專案（缺 {MARKER}）")
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise NotAProjectError(f"{MARKER} 損毀或格式錯誤：{exc}") from exc
    if marker.get("visionforge_project") is not True:
        raise NotAProjectError(f"{MARKER} 缺少 visionforge_project 標記")
    db = Database.open(root / "project.db")
    return Project(root, db)
