"""R3 Task-scoped DatasetVersion：只凍結已完整查核的教學真相。"""

from __future__ import annotations

import hashlib
from datetime import datetime

from visionforge_core.contracts import (
    ClassMapEntry,
    CoverageSnapshot,
    CoverageState,
    DatasetAnnotation,
    DatasetItem,
    DatasetVersion,
    ReadinessIssue,
    ReadinessReport,
)
from visionforge_core.storage import Project
from visionforge_core.storage.errors import NotFoundError


class DatasetNotReadyError(ValueError):
    def __init__(self, report: ReadinessReport) -> None:
        super().__init__("資料尚未符合凍結條件")
        self.report = report


def _split_by_group(
    group_ids: set[str], forced_train_groups: set[str] | None = None
) -> dict[str, str]:
    forced = forced_train_groups or set()
    ordered = sorted(
        group_ids - forced,
        key=lambda group: (hashlib.sha256(group.encode("utf-8")).hexdigest(), group),
    )
    validation_count = min(len(ordered), max(1, len(group_ids) // 5))
    validation = set(ordered[:validation_count])
    return {
        group: "validation" if group in validation else "train" for group in group_ids
    }


def _selected_concepts(project: Project, task_id: str, concept_ids: tuple[str, ...]):
    project.tasks.get(task_id)
    all_concepts = project.concepts.list_by_task(task_id)
    if not concept_ids:
        return all_concepts
    selected = [concept for concept in all_concepts if concept.concept_id in concept_ids]
    if len(selected) != len(set(concept_ids)):
        raise NotFoundError("部分 Concept 不屬於指定 Task")
    return selected


def inspect_readiness(
    project: Project,
    *,
    task_id: str,
    concept_ids: tuple[str, ...] = (),
) -> ReadinessReport:
    concepts = _selected_concepts(project, task_id, concept_ids)
    blockers: list[ReadinessIssue] = []
    warnings: list[ReadinessIssue] = []
    if not concepts:
        blockers.append(ReadinessIssue(code="no_concepts", message="此 Task 還沒有要訓練的物件"))
        return ReadinessReport(blockers=tuple(blockers))

    assignments = project.assignments.list_by_task(task_id)
    if not assignments:
        blockers.append(ReadinessIssue(code="no_media", message="此 Task 還沒有任何圖片"))
        return ReadinessReport(blockers=tuple(blockers))

    group_ids = {assignment.source_group_id for assignment in assignments}
    assignment_by_media = {item.media_hash: item for item in assignments}
    forced_train_groups = {
        assignment_by_media[feedback.media_hash].source_group_id
        for feedback in project.evaluation_feedback.list_by_task(task_id)
        if feedback.media_hash in assignment_by_media
    }
    if len(group_ids) < 2:
        blockers.append(
            ReadinessIssue(
                code="insufficient_source_groups",
                message="至少需要兩個獨立來源群組，才能分開訓練與驗證",
            )
        )
        group_split: dict[str, str] = {}
    else:
        group_split = _split_by_group(group_ids, forced_train_groups)
        if "validation" not in group_split.values():
            blockers.append(
                ReadinessIssue(
                    code="no_unseen_validation_group",
                    message="所有來源群組都曾由驗證錯誤回流；需要新的未見來源作為 validation",
                )
            )

    positive_by_concept = {concept.concept_id: 0 for concept in concepts}
    train_positive_by_concept = {concept.concept_id: 0 for concept in concepts}
    validation_positive_by_concept = {concept.concept_id: 0 for concept in concepts}

    for assignment in assignments:
        for concept in concepts:
            coverage = project.coverage.get(
                task_id, assignment.media_hash, concept.concept_id
            )
            if coverage is None or coverage.state is CoverageState.unverified:
                blockers.append(
                    ReadinessIssue(
                        code="unverified_coverage",
                        message=f"{concept.display_name} 在此圖片仍是尚未查核",
                        media_hash=assignment.media_hash,
                        concept_id=concept.concept_id,
                    )
                )
                continue
            annotations = project.annotations.list_effective(
                task_id, assignment.media_hash, concept.concept_id
            )
            if coverage.state is CoverageState.verified_complete and not annotations:
                blockers.append(
                    ReadinessIssue(
                        code="complete_without_annotations",
                        message="資料宣告已框完，但找不到有效框",
                        media_hash=assignment.media_hash,
                        concept_id=concept.concept_id,
                    )
                )
            if coverage.state is CoverageState.verified_absent and annotations:
                blockers.append(
                    ReadinessIssue(
                        code="absent_with_annotations",
                        message="資料宣告圖中沒有，但仍存在有效框",
                        media_hash=assignment.media_hash,
                        concept_id=concept.concept_id,
                    )
                )
            count = len(annotations)
            positive_by_concept[concept.concept_id] += count
            split = group_split.get(assignment.source_group_id)
            if split == "train":
                train_positive_by_concept[concept.concept_id] += count
            elif split == "validation":
                validation_positive_by_concept[concept.concept_id] += count

    for concept in concepts:
        concept_id = concept.concept_id
        if positive_by_concept[concept_id] == 0:
            blockers.append(
                ReadinessIssue(
                    code="no_positive_examples",
                    message=f"{concept.display_name} 還沒有任何正例框",
                    concept_id=concept_id,
                )
            )
        elif train_positive_by_concept[concept_id] == 0 and group_split:
            blockers.append(
                ReadinessIssue(
                    code="no_train_positive",
                    message=f"{concept.display_name} 的正例全落在驗證組，訓練組沒有可學素材",
                    concept_id=concept_id,
                )
            )
        if positive_by_concept[concept_id] < 20:
            warnings.append(
                ReadinessIssue(
                    code="few_positive_examples",
                    message=(
                        f"{concept.display_name} 目前只有 {positive_by_concept[concept_id]} 個框，"
                        "可先試鑄但方向與場景泛化可能很弱"
                    ),
                    concept_id=concept_id,
                )
            )
        if validation_positive_by_concept[concept_id] == 0 and group_split:
            warnings.append(
                ReadinessIssue(
                    code="no_validation_positive",
                    message=f"驗證組沒有 {concept.display_name} 正例，只能量到誤報，量不到漏報",
                    concept_id=concept_id,
                )
            )
    if 2 <= len(group_ids) < 5:
        warnings.append(
            ReadinessIssue(
                code="few_source_groups",
                message=f"目前只有 {len(group_ids)} 個獨立來源群組，驗證證據仍偏薄",
            )
        )
    return ReadinessReport(blockers=tuple(blockers), warnings=tuple(warnings))


def freeze_dataset(
    project: Project,
    *,
    dataset_version_id: str,
    task_id: str,
    created_at: datetime,
    concept_ids: tuple[str, ...] = (),
) -> tuple[DatasetVersion, ReadinessReport]:
    concepts = _selected_concepts(project, task_id, concept_ids)
    report = inspect_readiness(project, task_id=task_id, concept_ids=concept_ids)
    if not report.ready:
        raise DatasetNotReadyError(report)

    assignments = project.assignments.list_by_task(task_id)
    assignment_by_media = {item.media_hash: item for item in assignments}
    forced_train_groups = {
        assignment_by_media[feedback.media_hash].source_group_id
        for feedback in project.evaluation_feedback.list_by_task(task_id)
        if feedback.media_hash in assignment_by_media
    }
    group_split = _split_by_group(
        {item.source_group_id for item in assignments}, forced_train_groups
    )
    items: list[DatasetItem] = []
    for assignment in assignments:
        coverage_snapshots: list[CoverageSnapshot] = []
        annotations: list[DatasetAnnotation] = []
        for concept in concepts:
            coverage = project.coverage.get(
                task_id, assignment.media_hash, concept.concept_id
            )
            if coverage is None or coverage.state is CoverageState.unverified:
                raise RuntimeError("readiness 與 freeze 之間的 Coverage 狀態不一致")
            coverage_snapshots.append(
                CoverageSnapshot(
                    concept_id=concept.concept_id,
                    state=coverage.state.value,
                )
            )
            for annotation in project.annotations.list_effective(
                task_id, assignment.media_hash, concept.concept_id
            ):
                if annotation.bbox is None:
                    raise RuntimeError("effective annotation 不得缺 bbox")
                annotations.append(
                    DatasetAnnotation(
                        annotation_id=annotation.annotation_id,
                        revision_id=annotation.revision_id,
                        concept_id=annotation.concept_id,
                        bbox=annotation.bbox,
                        source=annotation.source,
                        source_claim_ref=annotation.source_claim_ref,
                    )
                )
        items.append(
            DatasetItem(
                media_hash=assignment.media_hash,
                source_group_id=assignment.source_group_id,
                split=group_split[assignment.source_group_id],
                coverage=tuple(sorted(coverage_snapshots, key=lambda item: item.concept_id)),
                annotations=tuple(sorted(annotations, key=lambda item: item.annotation_id)),
            )
        )

    latest = project.dataset_versions.latest(task_id)
    version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        version_number=1 if latest is None else latest.version_number + 1,
        task_id=task_id,
        concept_ids=tuple(concept.concept_id for concept in concepts),
        class_map=tuple(
            ClassMapEntry(
                concept_id=concept.concept_id,
                class_index=index,
                display_name=concept.display_name,
            )
            for index, concept in enumerate(concepts)
        ),
        items=tuple(sorted(items, key=lambda item: item.media_hash)),
        created_at=created_at,
        parent_ref=None if latest is None else latest.dataset_version_id,
    )
    project.dataset_versions.append(version)
    return version, report
