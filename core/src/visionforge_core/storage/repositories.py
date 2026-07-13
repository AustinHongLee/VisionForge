"""帳本儲存庫：append-only 的型別級落實。

本模組的每個 Repository **故意沒有 update 與 delete 方法**——
「歷史版本永不修改、永不刪除」（D5/D8）不靠紀律，靠介面上根本寫不出來。
重複身分寫入＝ConflictError（程式缺陷的訊號，不是可重試情況）。
"""

from __future__ import annotations

import json
import sqlite3

from visionforge_core.contracts import (
    AnnotationRevision,
    CalibrationSnapshot,
    CapabilityRelease,
    Claim,
    ClaimTeachingContext,
    ConceptDefinition,
    CostEntry,
    CoverageRecord,
    DatasetVersion,
    DatasetVersionManifest,
    DecisionOutcome,
    DecisionRecord,
    EvaluationFeedback,
    EvaluationReport,
    GoldenSetEntry,
    InferenceRun,
    Label,
    MediaAssignment,
    MediaRecord,
    ModelArtifact,
    ReviewEvent,
    TaskRecord,
    TaxonomyNode,
    TrainingRun,
    TrainingRunEvent,
)
from visionforge_core.storage.database import Database
from visionforge_core.storage.errors import ConflictError, NotFoundError


def _insert(db: Database, sql: str, params: tuple, identity: str) -> None:
    try:
        db.execute(sql, params)
    except sqlite3.IntegrityError as exc:
        raise ConflictError(f"帳本拒絕重複身分：{identity}") from exc


class MediaRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, record: MediaRecord) -> None:
        _insert(
            self._db,
            "INSERT INTO media(media_hash, imported_at, json) VALUES(?, ?, ?)",
            (record.media_hash, record.imported_at.isoformat(), record.model_dump_json()),
            f"media {record.media_hash[:12]}",
        )

    def get(self, media_hash: str) -> MediaRecord:
        row = self._db.query_one("SELECT json FROM media WHERE media_hash = ?", (media_hash,))
        if row is None:
            raise NotFoundError(f"media {media_hash[:12]} 不存在")
        return MediaRecord.model_validate_json(row["json"])

    def exists(self, media_hash: str) -> bool:
        return (
            self._db.query_one("SELECT 1 FROM media WHERE media_hash = ?", (media_hash,))
            is not None
        )

    def count(self) -> int:
        row = self._db.query_one("SELECT COUNT(*) AS n FROM media")
        return int(row["n"]) if row else 0

    def iter_recent(self, *, limit: int = 100, offset: int = 0) -> list[MediaRecord]:
        """最近匯入優先列舉（確定性排序：imported_at DESC，media_hash DESC 為次序）。"""
        rows = self._db.query_all(
            "SELECT json FROM media ORDER BY imported_at DESC, media_hash DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [MediaRecord.model_validate_json(row["json"]) for row in rows]


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, task: TaskRecord) -> None:
        _insert(
            self._db,
            "INSERT INTO tasks(task_id, name, created_at, json) VALUES(?, ?, ?, ?)",
            (task.task_id, task.name, task.created_at.isoformat(), task.model_dump_json()),
            f"task {task.name}",
        )

    def get(self, task_id: str) -> TaskRecord:
        row = self._db.query_one("SELECT json FROM tasks WHERE task_id = ?", (task_id,))
        if row is None:
            raise NotFoundError(f"task {task_id} 不存在")
        return TaskRecord.model_validate_json(row["json"])

    def list(self) -> list[TaskRecord]:
        rows = self._db.query_all("SELECT json FROM tasks ORDER BY created_at, task_id")
        return [TaskRecord.model_validate_json(row["json"]) for row in rows]


class ConceptRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, concept: ConceptDefinition) -> None:
        _insert(
            self._db,
            "INSERT INTO concepts(concept_id, task_id, display_name, created_at, json)"
            " VALUES(?, ?, ?, ?, ?)",
            (
                concept.concept_id,
                concept.task_id,
                concept.display_name,
                concept.created_at.isoformat(),
                concept.model_dump_json(),
            ),
            f"concept {concept.task_id}/{concept.display_name}",
        )

    def get(self, concept_id: str) -> ConceptDefinition:
        row = self._db.query_one(
            "SELECT json FROM concepts WHERE concept_id = ?", (concept_id,)
        )
        if row is None:
            raise NotFoundError(f"concept {concept_id} 不存在")
        return ConceptDefinition.model_validate_json(row["json"])

    def list_by_task(self, task_id: str) -> list[ConceptDefinition]:
        rows = self._db.query_all(
            "SELECT json FROM concepts WHERE task_id = ? ORDER BY created_at, concept_id",
            (task_id,),
        )
        return [ConceptDefinition.model_validate_json(row["json"]) for row in rows]


class MediaAssignmentRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, assignment: MediaAssignment) -> None:
        _insert(
            self._db,
            "INSERT INTO media_assignments(task_id, media_hash, source_group_id, assigned_at, json)"
            " VALUES(?, ?, ?, ?, ?)",
            (
                assignment.task_id,
                assignment.media_hash,
                assignment.source_group_id,
                assignment.assigned_at.isoformat(),
                assignment.model_dump_json(),
            ),
            f"assignment {assignment.task_id}/{assignment.media_hash[:12]}",
        )

    def get(self, task_id: str, media_hash: str) -> MediaAssignment | None:
        row = self._db.query_one(
            "SELECT json FROM media_assignments WHERE task_id = ? AND media_hash = ?",
            (task_id, media_hash),
        )
        return MediaAssignment.model_validate_json(row["json"]) if row else None

    def list_by_task(self, task_id: str) -> list[MediaAssignment]:
        rows = self._db.query_all(
            "SELECT json FROM media_assignments WHERE task_id = ?"
            " ORDER BY assigned_at, media_hash",
            (task_id,),
        )
        return [MediaAssignment.model_validate_json(row["json"]) for row in rows]


class CoverageRepository:
    """Coverage 是目前查核狀態；不可變 DatasetVersion 會保存每次訓練所見快照。"""

    def __init__(self, db: Database) -> None:
        self._db = db

    def set(self, coverage: CoverageRecord) -> None:
        self._db.execute(
            "INSERT INTO coverage(task_id, media_hash, concept_id, state, json)"
            " VALUES(?, ?, ?, ?, ?)"
            " ON CONFLICT(task_id, media_hash, concept_id) DO UPDATE SET"
            " state = excluded.state, json = excluded.json",
            (
                coverage.task_id,
                coverage.media_hash,
                coverage.concept_id,
                coverage.state.value,
                coverage.model_dump_json(),
            ),
        )

    def get(self, task_id: str, media_hash: str, concept_id: str) -> CoverageRecord | None:
        row = self._db.query_one(
            "SELECT json FROM coverage WHERE task_id = ? AND media_hash = ? AND concept_id = ?",
            (task_id, media_hash, concept_id),
        )
        return CoverageRecord.model_validate_json(row["json"]) if row else None

    def list_by_media(self, task_id: str, media_hash: str) -> list[CoverageRecord]:
        rows = self._db.query_all(
            "SELECT json FROM coverage WHERE task_id = ? AND media_hash = ?"
            " ORDER BY concept_id",
            (task_id, media_hash),
        )
        return [CoverageRecord.model_validate_json(row["json"]) for row in rows]


class AnnotationRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, revision: AnnotationRevision) -> None:
        _insert(
            self._db,
            "INSERT INTO annotation_revisions(revision_id, annotation_id, task_id, media_hash,"
            " concept_id, created_at, status, json) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (
                revision.revision_id,
                revision.annotation_id,
                revision.task_id,
                revision.media_hash,
                revision.concept_id,
                revision.created_at.isoformat(),
                revision.status,
                revision.model_dump_json(),
            ),
            f"annotation revision {revision.revision_id}",
        )

    def get_revision(self, revision_id: str) -> AnnotationRevision:
        row = self._db.query_one(
            "SELECT json FROM annotation_revisions WHERE revision_id = ?", (revision_id,)
        )
        if row is None:
            raise NotFoundError(f"annotation revision {revision_id} 不存在")
        return AnnotationRevision.model_validate_json(row["json"])

    def latest(self, annotation_id: str) -> AnnotationRevision:
        row = self._db.query_one(
            "SELECT json FROM annotation_revisions WHERE annotation_id = ?"
            " ORDER BY created_at DESC, revision_id DESC LIMIT 1",
            (annotation_id,),
        )
        if row is None:
            raise NotFoundError(f"annotation {annotation_id} 不存在")
        return AnnotationRevision.model_validate_json(row["json"])

    def list_effective(
        self,
        task_id: str,
        media_hash: str,
        concept_id: str | None = None,
    ) -> list[AnnotationRevision]:
        sql = (
            "SELECT json FROM annotation_revisions WHERE task_id = ? AND media_hash = ?"
        )
        params: tuple[str, ...] = (task_id, media_hash)
        if concept_id is not None:
            sql += " AND concept_id = ?"
            params += (concept_id,)
        sql += " ORDER BY created_at, revision_id"
        rows = self._db.query_all(sql, params)
        latest: dict[str, AnnotationRevision] = {}
        for row in rows:
            revision = AnnotationRevision.model_validate_json(row["json"])
            latest[revision.annotation_id] = revision
        return sorted(
            (revision for revision in latest.values() if revision.status == "active"),
            key=lambda revision: revision.annotation_id,
        )


class ClaimTeachingContextRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, context: ClaimTeachingContext) -> None:
        _insert(
            self._db,
            "INSERT INTO claim_teaching_context(claim_id, task_id, concept_id, json)"
            " VALUES(?, ?, ?, ?)",
            (context.claim_id, context.task_id, context.concept_id, context.model_dump_json()),
            f"claim teaching context {context.claim_id}",
        )

    def get(self, claim_id: str) -> ClaimTeachingContext:
        row = self._db.query_one(
            "SELECT json FROM claim_teaching_context WHERE claim_id = ?", (claim_id,)
        )
        if row is None:
            raise NotFoundError(f"claim teaching context {claim_id} 不存在")
        return ClaimTeachingContext.model_validate_json(row["json"])

    def latest_claims(self, task_id: str, media_hash: str) -> list[Claim]:
        """取得此教學範圍最近一次 Run 的教師建議。"""
        latest = self._db.query_one(
            "SELECT c.run_id FROM claim_teaching_context x"
            " JOIN claims c ON c.claim_id = x.claim_id"
            " JOIN runs r ON r.run_id = c.run_id"
            " WHERE x.task_id = ? AND c.media_hash = ?"
            " ORDER BY r.created_at DESC, r.run_id DESC LIMIT 1",
            (task_id, media_hash),
        )
        if latest is None:
            return []
        rows = self._db.query_all(
            "SELECT c.json FROM claims c JOIN claim_teaching_context x"
            " ON x.claim_id = c.claim_id WHERE c.run_id = ? AND x.task_id = ?"
            " ORDER BY c.claim_id",
            (latest["run_id"], task_id),
        )
        return [Claim.model_validate_json(row["json"]) for row in rows]


class RunRepository:
    """Run 與其 Claims 一體寫入（整批成功或整批不存在）。"""

    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, run: InferenceRun) -> None:
        with self._db.transaction():
            _insert(
                self._db,
                "INSERT INTO runs(run_id, media_hash, provider_id, provider_version,"
                " created_at, json) VALUES(?, ?, ?, ?, ?, ?)",
                (
                    run.run_id,
                    run.subject.media_hash,
                    run.producer.provider_id,
                    run.producer.provider_version,
                    run.created_at.isoformat(),
                    run.model_dump_json(),
                ),
                f"run {run.run_id}",
            )
            for claim in run.claims:
                _insert(
                    self._db,
                    "INSERT INTO claims(claim_id, run_id, media_hash, raw_confidence, json)"
                    " VALUES(?, ?, ?, ?, ?)",
                    (
                        claim.claim_id,
                        run.run_id,
                        run.subject.media_hash,
                        claim.confidence.raw,
                        claim.model_dump_json(),
                    ),
                    f"claim {claim.claim_id}",
                )

    def get(self, run_id: str) -> InferenceRun:
        row = self._db.query_one("SELECT json FROM runs WHERE run_id = ?", (run_id,))
        if row is None:
            raise NotFoundError(f"run {run_id} 不存在")
        return InferenceRun.model_validate_json(row["json"])

    def get_claim(self, claim_id: str) -> Claim:
        row = self._db.query_one("SELECT json FROM claims WHERE claim_id = ?", (claim_id,))
        if row is None:
            raise NotFoundError(f"claim {claim_id} 不存在")
        return Claim.model_validate_json(row["json"])

    def get_claim_context(self, claim_id: str) -> tuple[Claim, str, str]:
        """由持久化資料解析 Claim 的 run／media 關聯；不得信任 client 自行拼接。"""
        row = self._db.query_one(
            "SELECT json, run_id, media_hash FROM claims WHERE claim_id = ?",
            (claim_id,),
        )
        if row is None:
            raise NotFoundError(f"claim {claim_id} 不存在")
        return Claim.model_validate_json(row["json"]), row["run_id"], row["media_hash"]

    def iter_claims_by_media(self, media_hash: str) -> list[Claim]:
        rows = self._db.query_all(
            "SELECT json FROM claims WHERE media_hash = ? ORDER BY claim_id", (media_hash,)
        )
        return [Claim.model_validate_json(r["json"]) for r in rows]

    def iter_pending_review(self) -> list[tuple[Claim, str, str]]:
        """待審 claim（尚無任何 ReviewEvent）＋其 run_ref／media_hash。確定性排序。"""
        rows = self._db.query_all(
            "SELECT run_id, media_hash, json FROM claims "
            "WHERE claim_id NOT IN (SELECT claim_ref FROM review_events) "
            "ORDER BY claim_id"
        )
        return [
            (Claim.model_validate_json(r["json"]), r["run_id"], r["media_hash"]) for r in rows
        ]

    def iter_reviewed(self) -> list[tuple[Claim, str]]:
        """已審 claim＋其終局 to_status（校準觀測來源：approve/edit=correct、reject=incorrect）。"""
        rows = self._db.query_all(
            "SELECT c.json AS cj, e.json AS ej FROM claims c "
            "JOIN review_events e ON c.claim_id = e.claim_ref ORDER BY c.claim_id"
        )
        out: list[tuple[Claim, str]] = []
        for row in rows:
            claim = Claim.model_validate_json(row["cj"])
            event = ReviewEvent.model_validate_json(row["ej"])
            out.append((claim, event.to_status.value))
        return out


class LabelRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, label: Label) -> None:
        _insert(
            self._db,
            "INSERT INTO labels(label_id, claim_ref, media_hash, json) VALUES(?, ?, ?, ?)",
            (label.label_id, label.claim_ref, label.media_hash, label.model_dump_json()),
            f"label {label.label_id}",
        )

    def get(self, label_id: str) -> Label:
        row = self._db.query_one("SELECT json FROM labels WHERE label_id = ?", (label_id,))
        if row is None:
            raise NotFoundError(f"label {label_id} 不存在")
        return Label.model_validate_json(row["json"])

    def iter_by_media(self, media_hash: str) -> list[Label]:
        rows = self._db.query_all(
            "SELECT json FROM labels WHERE media_hash = ? ORDER BY label_id", (media_hash,)
        )
        return [Label.model_validate_json(r["json"]) for r in rows]

    def iter_all(self) -> list[Label]:
        """全部 Label（建 Dataset 版本快照用）；確定性排序。"""
        rows = self._db.query_all("SELECT json FROM labels ORDER BY label_id")
        return [Label.model_validate_json(r["json"]) for r in rows]


class DecisionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, record: DecisionRecord) -> None:
        _insert(
            self._db,
            "INSERT INTO decisions(decision_id, kind, at, json) VALUES(?, ?, ?, ?)",
            (record.decision_id, record.kind, record.at.isoformat(), record.model_dump_json()),
            f"decision {record.decision_id}",
        )

    def get(self, decision_id: str) -> DecisionRecord:
        row = self._db.query_one(
            "SELECT json FROM decisions WHERE decision_id = ?", (decision_id,)
        )
        if row is None:
            raise NotFoundError(f"decision {decision_id} 不存在")
        return DecisionRecord.model_validate_json(row["json"])

    def append_outcome(self, outcome: DecisionOutcome) -> None:
        _insert(
            self._db,
            "INSERT INTO decision_outcomes(outcome_id, decision_ref, json) VALUES(?, ?, ?)",
            (outcome.outcome_id, outcome.decision_ref, outcome.model_dump_json()),
            f"outcome {outcome.outcome_id}",
        )

    def iter_outcomes(self, decision_ref: str) -> list[DecisionOutcome]:
        rows = self._db.query_all(
            "SELECT json FROM decision_outcomes WHERE decision_ref = ? ORDER BY outcome_id",
            (decision_ref,),
        )
        return [DecisionOutcome.model_validate_json(r["json"]) for r in rows]


class CostRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, entry: CostEntry) -> None:
        _insert(
            self._db,
            "INSERT INTO costs(cost_id, phase, subject_kind, subject_id, json)"
            " VALUES(?, ?, ?, ?, ?)",
            (
                entry.cost_id,
                entry.phase,
                entry.subject.kind,
                entry.subject.id,
                entry.model_dump_json(),
            ),
            f"cost {entry.cost_id}",
        )

    def iter_by_subject(self, kind: str, subject_id: str) -> list[CostEntry]:
        rows = self._db.query_all(
            "SELECT json FROM costs WHERE subject_kind = ? AND subject_id = ?"
            " ORDER BY cost_id",
            (kind, subject_id),
        )
        return [CostEntry.model_validate_json(r["json"]) for r in rows]


class ReviewEventRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, event: ReviewEvent) -> None:
        _insert(
            self._db,
            "INSERT INTO review_events(event_id, claim_ref, at, json) VALUES(?, ?, ?, ?)",
            (event.event_id, event.claim_ref, event.at.isoformat(), event.model_dump_json()),
            f"review_event {event.event_id}",
        )

    def iter_by_claim(self, claim_ref: str) -> list[ReviewEvent]:
        rows = self._db.query_all(
            "SELECT json FROM review_events WHERE claim_ref = ? ORDER BY at, event_id",
            (claim_ref,),
        )
        return [ReviewEvent.model_validate_json(r["json"]) for r in rows]


class ManifestRepository:
    """Manifest 正規化儲存（header＋entries 分表），讀取時重組並**全量重新驗證**
    ——重組即體檢，損毀的版本讀不出來而不是悄悄用下去。"""

    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, manifest: DatasetVersionManifest) -> None:
        header = json.loads(manifest.model_dump_json())
        header["entries"] = []
        with self._db.transaction():
            _insert(
                self._db,
                "INSERT INTO manifests(version_id, version_number, created_at, json_header)"
                " VALUES(?, ?, ?, ?)",
                (
                    manifest.version_id,
                    manifest.version_number,
                    manifest.created_at.isoformat(),
                    json.dumps(header, ensure_ascii=False),
                ),
                f"manifest {manifest.version_id}（version_number 亦不得重複）",
            )
            for index, entry in enumerate(manifest.entries):
                _insert(
                    self._db,
                    "INSERT INTO manifest_entries(version_id, entry_index, media_hash,"
                    " split, label_refs) VALUES(?, ?, ?, ?, ?)",
                    (
                        manifest.version_id,
                        index,
                        entry.media_hash,
                        entry.split,
                        json.dumps(list(entry.label_refs)),
                    ),
                    f"manifest_entry {manifest.version_id}#{index}",
                )

    def get(self, version_id: str) -> DatasetVersionManifest:
        row = self._db.query_one(
            "SELECT json_header FROM manifests WHERE version_id = ?", (version_id,)
        )
        if row is None:
            raise NotFoundError(f"dataset version {version_id} 不存在")
        header = json.loads(row["json_header"])
        entry_rows = self._db.query_all(
            "SELECT media_hash, split, label_refs FROM manifest_entries"
            " WHERE version_id = ? ORDER BY entry_index",
            (version_id,),
        )
        header["entries"] = [
            {
                "media_hash": r["media_hash"],
                "split": r["split"],
                "label_refs": json.loads(r["label_refs"]),
            }
            for r in entry_rows
        ]
        return DatasetVersionManifest.model_validate(header)

    def latest(self) -> DatasetVersionManifest | None:
        row = self._db.query_one(
            "SELECT version_id FROM manifests ORDER BY version_number DESC LIMIT 1"
        )
        return self.get(row["version_id"]) if row else None


class GoldenRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, entry: GoldenSetEntry) -> None:
        _insert(
            self._db,
            "INSERT INTO golden_entries(entry_id, media_hash, status, json)"
            " VALUES(?, ?, ?, ?)",
            (entry.entry_id, entry.media_hash, entry.status, entry.model_dump_json()),
            f"golden_entry {entry.entry_id}",
        )

    def iter_active(self) -> list[GoldenSetEntry]:
        rows = self._db.query_all(
            "SELECT json FROM golden_entries WHERE status = 'active' ORDER BY entry_id"
        )
        return [GoldenSetEntry.model_validate_json(r["json"]) for r in rows]


class TaxonomyRepository:
    """概念登記（ADR-0010）：get-or-create raw_text→節點。append-only（不改不刪）。"""

    def __init__(self, db: Database) -> None:
        self._db = db

    def ensure(self, node: TaxonomyNode) -> TaxonomyNode:
        """raw_text 已登記則回既有節點；否則插入並回傳傳入節點。"""
        existing = self.get_by_text(node.raw_text)
        if existing is not None:
            return existing
        _insert(
            self._db,
            "INSERT INTO taxonomy(node_id, raw_text, created_at, json) VALUES(?, ?, ?, ?)",
            (node.node_id, node.raw_text, node.created_at.isoformat(), node.model_dump_json()),
            f"taxonomy {node.raw_text}",
        )
        return node

    def get_by_text(self, raw_text: str) -> TaxonomyNode | None:
        row = self._db.query_one("SELECT json FROM taxonomy WHERE raw_text = ?", (raw_text,))
        return TaxonomyNode.model_validate_json(row["json"]) if row else None

    def get(self, node_id: str) -> TaxonomyNode:
        row = self._db.query_one("SELECT json FROM taxonomy WHERE node_id = ?", (node_id,))
        if row is None:
            raise NotFoundError(f"taxonomy node {node_id} 不存在")
        return TaxonomyNode.model_validate_json(row["json"])

    def list(self) -> list[TaxonomyNode]:
        rows = self._db.query_all("SELECT json FROM taxonomy ORDER BY created_at, node_id")
        return [TaxonomyNode.model_validate_json(r["json"]) for r in rows]


class CalibrationRepository:
    """校準快照登記（ADR-0007/0010）：append-only；get_latest 取最新。"""

    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, snapshot: CalibrationSnapshot) -> None:
        _insert(
            self._db,
            "INSERT INTO calibrations(calibration_id, created_at, json) VALUES(?, ?, ?)",
            (snapshot.calibration_id, snapshot.created_at.isoformat(), snapshot.model_dump_json()),
            f"calibration {snapshot.calibration_id}",
        )

    def get_latest(self) -> CalibrationSnapshot | None:
        row = self._db.query_one(
            "SELECT json FROM calibrations ORDER BY created_at DESC, calibration_id DESC LIMIT 1"
        )
        return CalibrationSnapshot.model_validate_json(row["json"]) if row else None


class DatasetVersionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, version: DatasetVersion) -> None:
        _insert(
            self._db,
            "INSERT INTO teaching_dataset_versions(dataset_version_id, task_id, version_number,"
            " created_at, json) VALUES(?, ?, ?, ?, ?)",
            (
                version.dataset_version_id,
                version.task_id,
                version.version_number,
                version.created_at.isoformat(),
                version.model_dump_json(),
            ),
            f"dataset version {version.task_id}/v{version.version_number}",
        )

    def get(self, dataset_version_id: str) -> DatasetVersion:
        row = self._db.query_one(
            "SELECT json FROM teaching_dataset_versions WHERE dataset_version_id = ?",
            (dataset_version_id,),
        )
        if row is None:
            raise NotFoundError(f"dataset version {dataset_version_id} 不存在")
        return DatasetVersion.model_validate_json(row["json"])

    def list_by_task(self, task_id: str) -> list[DatasetVersion]:
        rows = self._db.query_all(
            "SELECT json FROM teaching_dataset_versions WHERE task_id = ?"
            " ORDER BY version_number",
            (task_id,),
        )
        return [DatasetVersion.model_validate_json(row["json"]) for row in rows]

    def latest(self, task_id: str) -> DatasetVersion | None:
        row = self._db.query_one(
            "SELECT json FROM teaching_dataset_versions WHERE task_id = ?"
            " ORDER BY version_number DESC LIMIT 1",
            (task_id,),
        )
        return DatasetVersion.model_validate_json(row["json"]) if row else None


class TrainingRunRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, run: TrainingRun) -> None:
        _insert(
            self._db,
            "INSERT INTO training_runs(training_run_id, dataset_version_id, task_id, created_at,"
            " json) VALUES(?, ?, ?, ?, ?)",
            (
                run.training_run_id,
                run.dataset_version_id,
                run.task_id,
                run.created_at.isoformat(),
                run.model_dump_json(),
            ),
            f"training run {run.training_run_id}",
        )

    def get(self, training_run_id: str) -> TrainingRun:
        row = self._db.query_one(
            "SELECT json FROM training_runs WHERE training_run_id = ?", (training_run_id,)
        )
        if row is None:
            raise NotFoundError(f"training run {training_run_id} 不存在")
        return TrainingRun.model_validate_json(row["json"])

    def list_by_task(self, task_id: str) -> list[TrainingRun]:
        rows = self._db.query_all(
            "SELECT json FROM training_runs WHERE task_id = ? ORDER BY created_at, training_run_id",
            (task_id,),
        )
        return [TrainingRun.model_validate_json(row["json"]) for row in rows]

    def append_event(self, event: TrainingRunEvent) -> None:
        _insert(
            self._db,
            "INSERT INTO training_run_events(event_id, training_run_id, status, at, json)"
            " VALUES(?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.training_run_id,
                event.status,
                event.at.isoformat(),
                event.model_dump_json(),
            ),
            f"training event {event.event_id}",
        )

    def events(self, training_run_id: str) -> list[TrainingRunEvent]:
        rows = self._db.query_all(
            "SELECT json FROM training_run_events WHERE training_run_id = ?"
            " ORDER BY at, event_id",
            (training_run_id,),
        )
        return [TrainingRunEvent.model_validate_json(row["json"]) for row in rows]

    def latest_event(self, training_run_id: str) -> TrainingRunEvent:
        row = self._db.query_one(
            "SELECT json FROM training_run_events WHERE training_run_id = ?"
            " ORDER BY at DESC, event_id DESC LIMIT 1",
            (training_run_id,),
        )
        if row is None:
            raise NotFoundError(f"training run {training_run_id} 尚無狀態")
        return TrainingRunEvent.model_validate_json(row["json"])

    def list_with_status(self, status: str) -> list[TrainingRun]:
        rows = self._db.query_all(
            "SELECT r.json FROM training_runs r JOIN training_run_events e"
            " ON e.training_run_id = r.training_run_id"
            " WHERE e.status = ? AND e.event_id = ("
            " SELECT e2.event_id FROM training_run_events e2"
            " WHERE e2.training_run_id = r.training_run_id"
            " ORDER BY e2.at DESC, e2.event_id DESC LIMIT 1)"
            " ORDER BY r.created_at, r.training_run_id",
            (status,),
        )
        return [TrainingRun.model_validate_json(row["json"]) for row in rows]


class ModelArtifactRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, artifact: ModelArtifact) -> None:
        _insert(
            self._db,
            "INSERT INTO model_artifacts(artifact_id, artifact_hash, task_id, dataset_version_id,"
            " training_run_id, created_at, json) VALUES(?, ?, ?, ?, ?, ?, ?)",
            (
                artifact.artifact_id,
                artifact.artifact_hash,
                artifact.task_id,
                artifact.dataset_version_id,
                artifact.training_run_id,
                artifact.created_at.isoformat(),
                artifact.model_dump_json(),
            ),
            f"model artifact {artifact.artifact_id}",
        )

    def get(self, artifact_id: str) -> ModelArtifact:
        row = self._db.query_one(
            "SELECT json FROM model_artifacts WHERE artifact_id = ?", (artifact_id,)
        )
        if row is None:
            raise NotFoundError(f"model artifact {artifact_id} 不存在")
        return ModelArtifact.model_validate_json(row["json"])

    def list_by_task(self, task_id: str) -> list[ModelArtifact]:
        rows = self._db.query_all(
            "SELECT json FROM model_artifacts WHERE task_id = ? ORDER BY created_at, artifact_id",
            (task_id,),
        )
        return [ModelArtifact.model_validate_json(row["json"]) for row in rows]

    def by_run(self, training_run_id: str) -> ModelArtifact | None:
        row = self._db.query_one(
            "SELECT json FROM model_artifacts WHERE training_run_id = ?"
            " ORDER BY created_at, artifact_id LIMIT 1",
            (training_run_id,),
        )
        return ModelArtifact.model_validate_json(row["json"]) if row else None


class EvaluationRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, report: EvaluationReport) -> None:
        _insert(
            self._db,
            "INSERT INTO evaluation_reports(evaluation_id, artifact_id, dataset_version_id,"
            " created_at, json) VALUES(?, ?, ?, ?, ?)",
            (
                report.evaluation_id,
                report.artifact_id,
                report.dataset_version_id,
                report.created_at.isoformat(),
                report.model_dump_json(),
            ),
            f"evaluation {report.evaluation_id}",
        )

    def get(self, evaluation_id: str) -> EvaluationReport:
        row = self._db.query_one(
            "SELECT json FROM evaluation_reports WHERE evaluation_id = ?", (evaluation_id,)
        )
        if row is None:
            raise NotFoundError(f"evaluation {evaluation_id} 不存在")
        return EvaluationReport.model_validate_json(row["json"])

    def latest_for_artifact(self, artifact_id: str) -> EvaluationReport | None:
        row = self._db.query_one(
            "SELECT json FROM evaluation_reports WHERE artifact_id = ?"
            " ORDER BY created_at DESC, evaluation_id DESC LIMIT 1",
            (artifact_id,),
        )
        return EvaluationReport.model_validate_json(row["json"]) if row else None


class EvaluationFeedbackRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, feedback: EvaluationFeedback) -> None:
        _insert(
            self._db,
            "INSERT INTO evaluation_feedback(feedback_id, evaluation_id, artifact_id, task_id,"
            " media_hash, created_at, json) VALUES(?, ?, ?, ?, ?, ?, ?)",
            (
                feedback.feedback_id,
                feedback.evaluation_id,
                feedback.artifact_id,
                feedback.task_id,
                feedback.media_hash,
                feedback.created_at.isoformat(),
                feedback.model_dump_json(),
            ),
            f"evaluation feedback {feedback.evaluation_id}/{feedback.media_hash[:12]}",
        )

    def list_by_task(self, task_id: str) -> list[EvaluationFeedback]:
        rows = self._db.query_all(
            "SELECT json FROM evaluation_feedback WHERE task_id = ?"
            " ORDER BY created_at, feedback_id",
            (task_id,),
        )
        return [EvaluationFeedback.model_validate_json(row["json"]) for row in rows]


class CapabilityReleaseRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, release: CapabilityRelease) -> None:
        _insert(
            self._db,
            "INSERT INTO capability_releases(release_id, task_id, version_number, created_at, json)"
            " VALUES(?, ?, ?, ?, ?)",
            (
                release.release_id,
                release.task_id,
                release.version_number,
                release.created_at.isoformat(),
                release.model_dump_json(),
            ),
            f"capability release {release.task_id}/v{release.version_number}",
        )

    def get(self, release_id: str) -> CapabilityRelease:
        row = self._db.query_one(
            "SELECT json FROM capability_releases WHERE release_id = ?", (release_id,)
        )
        if row is None:
            raise NotFoundError(f"capability release {release_id} 不存在")
        return CapabilityRelease.model_validate_json(row["json"])

    def list_by_task(self, task_id: str) -> list[CapabilityRelease]:
        rows = self._db.query_all(
            "SELECT json FROM capability_releases WHERE task_id = ? ORDER BY version_number",
            (task_id,),
        )
        return [CapabilityRelease.model_validate_json(row["json"]) for row in rows]

    def latest(self, task_id: str) -> CapabilityRelease | None:
        row = self._db.query_one(
            "SELECT json FROM capability_releases WHERE task_id = ?"
            " ORDER BY version_number DESC LIMIT 1",
            (task_id,),
        )
        return CapabilityRelease.model_validate_json(row["json"]) if row else None
