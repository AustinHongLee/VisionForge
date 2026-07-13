"""R3 教學領域服務；只接受伺服器已確認的 Task/Concept/Media/Claim 關聯。"""

from __future__ import annotations

from datetime import datetime

from visionforge_core.contracts import (
    AnnotationRevision,
    AnnotationSource,
    BBox,
    ConceptDefinition,
    CoverageRecord,
    CoverageState,
    MediaAssignment,
    TaskRecord,
)
from visionforge_core.storage import Project
from visionforge_core.storage.errors import ConflictError, NotFoundError


def add_task(
    project: Project,
    *,
    task_id: str,
    name: str,
    created_at: datetime,
) -> TaskRecord:
    task = TaskRecord(task_id=task_id, name=name.strip(), created_at=created_at)
    project.tasks.add(task)
    return task


def add_concept(
    project: Project,
    *,
    concept_id: str,
    task_id: str,
    display_name: str,
    aliases: tuple[str, ...] = (),
    created_at: datetime,
) -> ConceptDefinition:
    project.tasks.get(task_id)
    concept = ConceptDefinition(
        concept_id=concept_id,
        task_id=task_id,
        display_name=display_name.strip(),
        aliases=aliases,
        created_at=created_at,
    )
    project.concepts.add(concept)
    return concept


def assign_media(
    project: Project,
    *,
    task_id: str,
    media_hash: str,
    source_group_id: str,
    assigned_at: datetime,
) -> MediaAssignment:
    project.tasks.get(task_id)
    project.media.get(media_hash)
    existing = project.assignments.get(task_id, media_hash)
    if existing is not None:
        if existing.source_group_id != source_group_id:
            raise ConflictError("媒體已屬於此 Task，但 source_group_id 不同")
        return existing
    assignment = MediaAssignment(
        task_id=task_id,
        media_hash=media_hash,
        source_group_id=source_group_id,
        assigned_at=assigned_at,
    )
    project.assignments.add(assignment)
    return assignment


def _require_scope(project: Project, task_id: str, media_hash: str, concept_id: str) -> None:
    project.tasks.get(task_id)
    concept = project.concepts.get(concept_id)
    if concept.task_id != task_id:
        raise ConflictError("Concept 不屬於指定 Task")
    if project.assignments.get(task_id, media_hash) is None:
        raise NotFoundError("媒體尚未加入指定 Task")


def get_coverage(
    project: Project,
    *,
    task_id: str,
    media_hash: str,
    concept_id: str,
) -> CoverageRecord:
    _require_scope(project, task_id, media_hash, concept_id)
    return project.coverage.get(task_id, media_hash, concept_id) or CoverageRecord(
        task_id=task_id,
        media_hash=media_hash,
        concept_id=concept_id,
    )


def set_coverage(
    project: Project,
    *,
    task_id: str,
    media_hash: str,
    concept_id: str,
    state: CoverageState,
    reviewer: str | None = None,
    verified_at: datetime | None = None,
) -> CoverageRecord:
    _require_scope(project, task_id, media_hash, concept_id)
    active_count = len(project.annotations.list_effective(task_id, media_hash, concept_id))
    if state is CoverageState.verified_complete and active_count == 0:
        raise ConflictError("沒有有效標註，不能宣告 verified_complete")
    if state is CoverageState.verified_absent and active_count != 0:
        raise ConflictError("仍有有效標註，不能宣告 verified_absent")
    record = CoverageRecord(
        task_id=task_id,
        media_hash=media_hash,
        concept_id=concept_id,
        state=state,
        reviewer=reviewer,
        verified_at=verified_at,
    )
    project.coverage.set(record)
    return record


def _mark_unverified(
    project: Project, *, task_id: str, media_hash: str, concept_id: str
) -> None:
    project.coverage.set(
        CoverageRecord(task_id=task_id, media_hash=media_hash, concept_id=concept_id)
    )


def add_annotation(
    project: Project,
    *,
    revision_id: str,
    annotation_id: str,
    task_id: str,
    media_hash: str,
    concept_id: str,
    bbox: BBox | None,
    created_by: str,
    created_at: datetime,
    source_claim_ref: str | None = None,
) -> AnnotationRevision:
    _require_scope(project, task_id, media_hash, concept_id)
    source = AnnotationSource.manual
    if source_claim_ref is not None:
        claim, _, claim_media_hash = project.runs.get_claim_context(source_claim_ref)
        context = project.claim_teaching_context.get(source_claim_ref)
        if (
            context.task_id != task_id
            or context.concept_id != concept_id
            or claim_media_hash != media_hash
        ):
            raise ConflictError("教師 Claim 與標註的 Task/Concept/Media 不一致")
        if not isinstance(claim.geometry, BBox):
            raise ConflictError("目前 detect 教學只接受 bbox Claim")
        if bbox is None:
            bbox = claim.geometry
        source = (
            AnnotationSource.teacher_accepted
            if bbox == claim.geometry
            else AnnotationSource.teacher_edited
        )
    if bbox is None:
        raise ValueError("手動標註必須提供 bbox")
    revision = AnnotationRevision(
        revision_id=revision_id,
        annotation_id=annotation_id,
        task_id=task_id,
        concept_id=concept_id,
        media_hash=media_hash,
        bbox=bbox,
        source=source,
        source_claim_ref=source_claim_ref,
        created_by=created_by,
        created_at=created_at,
    )
    with project.db.transaction():
        project.annotations.append(revision)
        _mark_unverified(
            project, task_id=task_id, media_hash=media_hash, concept_id=concept_id
        )
    return revision


def edit_annotation(
    project: Project,
    *,
    annotation_id: str,
    revision_id: str,
    concept_id: str,
    bbox: BBox,
    created_by: str,
    created_at: datetime,
) -> AnnotationRevision:
    previous = project.annotations.latest(annotation_id)
    if previous.status != "active":
        raise ConflictError("已撤回的標註不能再編輯")
    _require_scope(project, previous.task_id, previous.media_hash, concept_id)
    source = (
        AnnotationSource.teacher_edited
        if previous.source_claim_ref is not None
        else AnnotationSource.manual
    )
    revision = AnnotationRevision(
        revision_id=revision_id,
        annotation_id=annotation_id,
        task_id=previous.task_id,
        concept_id=concept_id,
        media_hash=previous.media_hash,
        bbox=bbox,
        source=source,
        source_claim_ref=previous.source_claim_ref,
        created_by=created_by,
        created_at=created_at,
        replaces_revision_id=previous.revision_id,
    )
    with project.db.transaction():
        project.annotations.append(revision)
        _mark_unverified(
            project,
            task_id=previous.task_id,
            media_hash=previous.media_hash,
            concept_id=previous.concept_id,
        )
        if concept_id != previous.concept_id:
            _mark_unverified(
                project,
                task_id=previous.task_id,
                media_hash=previous.media_hash,
                concept_id=concept_id,
            )
    return revision


def retract_annotation(
    project: Project,
    *,
    annotation_id: str,
    revision_id: str,
    created_by: str,
    created_at: datetime,
) -> AnnotationRevision:
    previous = project.annotations.latest(annotation_id)
    if previous.status != "active":
        raise ConflictError("標註已撤回")
    revision = AnnotationRevision(
        revision_id=revision_id,
        annotation_id=annotation_id,
        task_id=previous.task_id,
        concept_id=previous.concept_id,
        media_hash=previous.media_hash,
        bbox=None,
        source=previous.source,
        source_claim_ref=previous.source_claim_ref,
        created_by=created_by,
        created_at=created_at,
        replaces_revision_id=previous.revision_id,
        status="retracted",
    )
    with project.db.transaction():
        project.annotations.append(revision)
        _mark_unverified(
            project,
            task_id=previous.task_id,
            media_hash=previous.media_hash,
            concept_id=previous.concept_id,
        )
    return revision
