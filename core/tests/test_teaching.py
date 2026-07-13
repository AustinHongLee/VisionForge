"""R3 教學領域：Task/Concept/Coverage/Annotation Revision 的核心不變量。"""

from datetime import datetime, timedelta, timezone

import pytest
from visionforge_core.contracts import (
    BBox,
    Claim,
    ClaimTeachingContext,
    Concept,
    Confidence,
    CoverageState,
    InferenceRun,
    MediaRecord,
    MediaSource,
    MediaSubject,
    Producer,
)
from visionforge_core.storage import ConflictError, NotFoundError, create_project
from visionforge_core.teaching import (
    add_annotation,
    add_concept,
    add_task,
    assign_media,
    edit_annotation,
    get_coverage,
    retract_annotation,
    set_coverage,
)

NOW = datetime(2026, 7, 13, 1, 0, tzinfo=timezone.utc)


def ulid(n: int) -> str:
    return f"{n:026d}"


def sha(n: int) -> str:
    return f"{n:064x}"


@pytest.fixture()
def project(tmp_path):
    project = create_project(tmp_path / "project", "forge", ulid(1))
    project.media.add(
        MediaRecord(
            media_hash=sha(1),
            width_px=1000,
            height_px=800,
            format="png",
            byte_size=100,
            imported_at=NOW,
            source=MediaSource(kind="file", detail="drawing.png"),
            exif_normalized=True,
        )
    )
    add_task(project, task_id=ulid(10), name="閥件偵測", created_at=NOW)
    add_concept(
        project,
        concept_id=ulid(20),
        task_id=ulid(10),
        display_name="Gate Valve",
        created_at=NOW,
    )
    assign_media(
        project,
        task_id=ulid(10),
        media_hash=sha(1),
        source_group_id="drawing-001",
        assigned_at=NOW,
    )
    yield project
    project.close()


def box(x1: float = 0.1) -> BBox:
    return BBox(x1=x1, y1=0.2, x2=x1 + 0.2, y2=0.5)


def test_task_concept_assignment_and_implicit_unverified(project):
    assert project.tasks.get(ulid(10)).name == "閥件偵測"
    assert project.concepts.list_by_task(ulid(10))[0].display_name == "Gate Valve"
    assert project.assignments.get(ulid(10), sha(1)).source_group_id == "drawing-001"
    coverage = get_coverage(
        project, task_id=ulid(10), media_hash=sha(1), concept_id=ulid(20)
    )
    assert coverage.state is CoverageState.unverified


def test_concept_is_task_scoped(project):
    add_task(project, task_id=ulid(11), name="另一任務", created_at=NOW)
    with pytest.raises(ConflictError, match="不屬於"):
        get_coverage(project, task_id=ulid(11), media_hash=sha(1), concept_id=ulid(20))


def test_complete_and_absent_follow_effective_annotations(project):
    with pytest.raises(ConflictError, match="沒有有效標註"):
        set_coverage(
            project,
            task_id=ulid(10),
            media_hash=sha(1),
            concept_id=ulid(20),
            state=CoverageState.verified_complete,
            reviewer="owner",
            verified_at=NOW,
        )
    annotation = add_annotation(
        project,
        revision_id=ulid(30),
        annotation_id=ulid(31),
        task_id=ulid(10),
        media_hash=sha(1),
        concept_id=ulid(20),
        bbox=box(),
        created_by="owner",
        created_at=NOW,
    )
    assert annotation.source.value == "manual"
    complete = set_coverage(
        project,
        task_id=ulid(10),
        media_hash=sha(1),
        concept_id=ulid(20),
        state=CoverageState.verified_complete,
        reviewer="owner",
        verified_at=NOW,
    )
    assert complete.state is CoverageState.verified_complete
    with pytest.raises(ConflictError, match="仍有有效標註"):
        set_coverage(
            project,
            task_id=ulid(10),
            media_hash=sha(1),
            concept_id=ulid(20),
            state=CoverageState.verified_absent,
            reviewer="owner",
            verified_at=NOW,
        )


def test_edit_and_retract_are_append_only_revisions(project):
    first = add_annotation(
        project,
        revision_id=ulid(30),
        annotation_id=ulid(31),
        task_id=ulid(10),
        media_hash=sha(1),
        concept_id=ulid(20),
        bbox=box(),
        created_by="owner",
        created_at=NOW,
    )
    second = edit_annotation(
        project,
        annotation_id=first.annotation_id,
        revision_id=ulid(32),
        concept_id=ulid(20),
        bbox=box(0.3),
        created_by="owner",
        created_at=NOW + timedelta(seconds=1),
    )
    assert second.replaces_revision_id == first.revision_id
    assert project.annotations.get_revision(first.revision_id) == first
    assert project.annotations.list_effective(ulid(10), sha(1)) == [second]
    removed = retract_annotation(
        project,
        annotation_id=first.annotation_id,
        revision_id=ulid(33),
        created_by="owner",
        created_at=NOW + timedelta(seconds=2),
    )
    assert removed.status == "retracted"
    assert project.annotations.list_effective(ulid(10), sha(1)) == []
    absent = set_coverage(
        project,
        task_id=ulid(10),
        media_hash=sha(1),
        concept_id=ulid(20),
        state=CoverageState.verified_absent,
        reviewer="owner",
        verified_at=NOW + timedelta(seconds=3),
    )
    assert absent.state is CoverageState.verified_absent


def test_teacher_annotation_requires_persisted_context(project):
    claim = Claim(
        claim_id=ulid(40),
        geometry=box(),
        concept=Concept(raw_text="Gate Valve"),
        confidence=Confidence(raw=0.8),
    )
    project.runs.append(
        InferenceRun(
            run_id=ulid(41),
            subject=MediaSubject(media_hash=sha(1), width_px=1000, height_px=800),
            producer=Producer(provider_id="teacher", provider_version="1", params_hash=sha(9)),
            task="detect",
            created_at=NOW,
            duration_ms=1,
            cost_ref=ulid(42),
            decision_ref=ulid(43),
            claims=(claim,),
        )
    )
    with pytest.raises(NotFoundError, match="teaching context"):
        add_annotation(
            project,
            revision_id=ulid(44),
            annotation_id=ulid(45),
            task_id=ulid(10),
            media_hash=sha(1),
            concept_id=ulid(20),
            bbox=None,
            source_claim_ref=claim.claim_id,
            created_by="owner",
            created_at=NOW,
        )
    project.claim_teaching_context.add(
        ClaimTeachingContext(
            claim_id=claim.claim_id, task_id=ulid(10), concept_id=ulid(20)
        )
    )
    accepted = add_annotation(
        project,
        revision_id=ulid(44),
        annotation_id=ulid(45),
        task_id=ulid(10),
        media_hash=sha(1),
        concept_id=ulid(20),
        bbox=None,
        source_claim_ref=claim.claim_id,
        created_by="owner",
        created_at=NOW,
    )
    assert accepted.source.value == "teacher_accepted"
    assert accepted.bbox == claim.geometry


def test_annotation_and_coverage_change_are_atomic(project, monkeypatch):
    def fail(_record):
        raise RuntimeError("fault injection")

    monkeypatch.setattr(project.coverage, "set", fail)
    with pytest.raises(RuntimeError, match="fault injection"):
        add_annotation(
            project,
            revision_id=ulid(30),
            annotation_id=ulid(31),
            task_id=ulid(10),
            media_hash=sha(1),
            concept_id=ulid(20),
            bbox=box(),
            created_by="owner",
            created_at=NOW,
        )
    with pytest.raises(NotFoundError):
        project.annotations.latest(ulid(31))
