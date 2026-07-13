"""SQLite 基座：連線、交易、遷移（D9）。

文件式儲存原則（ADR-0005）：**契約 JSON 是權威資料，關聯欄位只是查詢索引。**
好處：Pydantic 契約與儲存格式單一事實來源，不會出現雙 schema 漂移；
每筆記錄自帶 schema_version，N/N-1 相容在讀取端處理（PR2）。
儲存層對大型結構（Manifest entries）做正規化，屬效能手段，不改變邏輯格式。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from visionforge_core.storage.errors import ProjectSchemaTooNewError

_V0001 = """
CREATE TABLE media(
    media_hash TEXT PRIMARY KEY,
    imported_at TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE TABLE runs(
    run_id TEXT PRIMARY KEY,
    media_hash TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    provider_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE INDEX idx_runs_media ON runs(media_hash);
CREATE TABLE claims(
    claim_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    media_hash TEXT NOT NULL,
    raw_confidence REAL NOT NULL,
    json TEXT NOT NULL
);
CREATE INDEX idx_claims_run ON claims(run_id);
CREATE INDEX idx_claims_media ON claims(media_hash);
CREATE TABLE labels(
    label_id TEXT PRIMARY KEY,
    claim_ref TEXT NOT NULL,
    media_hash TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE INDEX idx_labels_media ON labels(media_hash);
CREATE TABLE decisions(
    decision_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    at TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE TABLE decision_outcomes(
    outcome_id TEXT PRIMARY KEY,
    decision_ref TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE INDEX idx_outcomes_decision ON decision_outcomes(decision_ref);
CREATE TABLE costs(
    cost_id TEXT PRIMARY KEY,
    phase TEXT NOT NULL,
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE INDEX idx_costs_subject ON costs(subject_kind, subject_id);
CREATE TABLE review_events(
    event_id TEXT PRIMARY KEY,
    claim_ref TEXT NOT NULL,
    at TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE INDEX idx_review_claim ON review_events(claim_ref);
CREATE TABLE manifests(
    version_id TEXT PRIMARY KEY,
    version_number INTEGER NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    json_header TEXT NOT NULL
);
CREATE TABLE manifest_entries(
    version_id TEXT NOT NULL REFERENCES manifests(version_id),
    entry_index INTEGER NOT NULL,
    media_hash TEXT NOT NULL,
    split TEXT NOT NULL,
    label_refs TEXT NOT NULL,
    PRIMARY KEY(version_id, entry_index)
);
CREATE INDEX idx_manifest_entries_media ON manifest_entries(media_hash);
CREATE TABLE golden_entries(
    entry_id TEXT PRIMARY KEY,
    media_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    json TEXT NOT NULL
);
"""

_V0002 = """
CREATE TABLE taxonomy(
    node_id TEXT PRIMARY KEY,
    raw_text TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    json TEXT NOT NULL
);
"""

_V0003 = """
CREATE TABLE calibrations(
    calibration_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    json TEXT NOT NULL
);
"""

_V0004 = """
CREATE TABLE tasks(
    task_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE TABLE concepts(
    concept_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    json TEXT NOT NULL,
    UNIQUE(task_id, display_name)
);
CREATE INDEX idx_concepts_task ON concepts(task_id);
CREATE TABLE media_assignments(
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    media_hash TEXT NOT NULL REFERENCES media(media_hash),
    source_group_id TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    json TEXT NOT NULL,
    PRIMARY KEY(task_id, media_hash)
);
CREATE INDEX idx_assignments_group ON media_assignments(task_id, source_group_id);
CREATE TABLE coverage(
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    media_hash TEXT NOT NULL REFERENCES media(media_hash),
    concept_id TEXT NOT NULL REFERENCES concepts(concept_id),
    state TEXT NOT NULL,
    json TEXT NOT NULL,
    PRIMARY KEY(task_id, media_hash, concept_id)
);
CREATE INDEX idx_coverage_task_state ON coverage(task_id, state);
CREATE TABLE annotation_revisions(
    revision_id TEXT PRIMARY KEY,
    annotation_id TEXT NOT NULL,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    media_hash TEXT NOT NULL REFERENCES media(media_hash),
    concept_id TEXT NOT NULL REFERENCES concepts(concept_id),
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE INDEX idx_annotations_scope ON annotation_revisions(task_id, media_hash, concept_id);
CREATE INDEX idx_annotations_identity ON annotation_revisions(annotation_id, created_at);
CREATE TABLE claim_teaching_context(
    claim_id TEXT PRIMARY KEY REFERENCES claims(claim_id),
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    concept_id TEXT NOT NULL REFERENCES concepts(concept_id),
    json TEXT NOT NULL
);
CREATE INDEX idx_claim_context_scope ON claim_teaching_context(task_id, concept_id);
"""

# 遷移只增不改：新版本＝追加項目（D9：任何歷史專案永遠打得開）。
MIGRATIONS: tuple[tuple[int, str], ...] = (
    (1, _V0001),
    (2, _V0002),
    (3, _V0003),
    (4, _V0004),
)
MAX_SCHEMA = MIGRATIONS[-1][0]


class Database:
    """單一連線的薄封裝。Worker 各自開自己的連線（PR4 程序隔離）。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._savepoint_counter = 0

    @classmethod
    def open(cls, db_path: Path) -> Database:
        conn = sqlite3.connect(str(db_path), isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        db = cls(conn)
        db._migrate()
        return db

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """明確交易：整批成功或整批不存在（D5 版本化交易的基座）。"""
        if self._conn.in_transaction:
            self._savepoint_counter += 1
            name = f"visionforge_sp_{self._savepoint_counter}"
            self._conn.execute(f"SAVEPOINT {name}")
            try:
                yield
            except BaseException:
                self._conn.execute(f"ROLLBACK TO {name}")
                self._conn.execute(f"RELEASE {name}")
                raise
            self._conn.execute(f"RELEASE {name}")
            return

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise
        self._conn.execute("COMMIT")

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self._conn.execute(sql, params).fetchone()

    def query_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchall()

    def _migrate(self) -> None:
        self.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations("
            "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        row = self.query_one("SELECT MAX(version) AS v FROM schema_migrations")
        current = row["v"] if row and row["v"] is not None else 0
        if current > MAX_SCHEMA:
            raise ProjectSchemaTooNewError(
                f"專案資料庫 schema v{current} 高於本程式支援的 v{MAX_SCHEMA}——"
                "此專案由較新版本建立，請升級應用程式（D9）"
            )
        for version, script in MIGRATIONS:
            if version <= current:
                continue
            with self.transaction():
                for statement in script.split(";"):
                    stmt = statement.strip()
                    if stmt:
                        self._conn.execute(stmt)
                self._conn.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                    (version, datetime.now(timezone.utc).isoformat()),
                )
