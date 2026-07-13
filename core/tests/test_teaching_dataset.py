"""R3 Task-scoped DatasetVersion readiness、分組切分與不可變快照。"""

from datetime import datetime, timedelta, timezone

import pytest
from visionforge_core.contracts import BBox, CoverageState, MediaRecord, MediaSource
from visionforge_core.dataset import DatasetNotReadyError, freeze_dataset, inspect_readiness
from visionforge_core.storage import create_project
from visionforge_core.teaching import (
    add_annotation,
    add_concept,
    add_task,
    assign_media,
    edit_annotation,
    set_coverage,
)

NOW = datetime(2026, 7, 13, 2, 0, tzinfo=timezone.utc)


def ulid(n: int) -> str:
    return f"{n:026d}"


def sha(n: int) -> str:
    return f"{n:064x}"


def bbox(x1: float) -> BBox:
    return BBox(x1=x1, y1=0.1, x2=x1 + 0.2, y2=0.4)


@pytest.fixture()
def ready_project(tmp_path):
    project = create_project(tmp_path / "project", "freeze", ulid(1))
    add_task(project, task_id=ulid(10), name="detect", created_at=NOW)
    add_concept(
        project,
        concept_id=ulid(20),
        task_id=ulid(10),
        display_name="A",
        created_at=NOW,
    )
    for index in (1, 2):
        project.media.add(
            MediaRecord(
                media_hash=sha(index),
                width_px=640,
                height_px=480,
                format="png",
                byte_size=100,
                imported_at=NOW,
                source=MediaSource(kind="file", detail=f"{index}.png"),
                exif_normalized=True,
            )
        )
        assign_media(
            project,
            task_id=ulid(10),
            media_hash=sha(index),
            source_group_id=f"source-{index}",
            assigned_at=NOW,
        )
        add_annotation(
            project,
            revision_id=ulid(30 + index),
            annotation_id=ulid(40 + index),
            task_id=ulid(10),
            media_hash=sha(index),
            concept_id=ulid(20),
            bbox=bbox(index / 10),
            created_by="user",
            created_at=NOW,
        )
        set_coverage(
            project,
            task_id=ulid(10),
            media_hash=sha(index),
            concept_id=ulid(20),
            state=CoverageState.verified_complete,
            reviewer="user",
            verified_at=NOW,
        )
    yield project
    project.close()


def test_freeze_is_task_scoped_group_safe_and_immutable(ready_project):
    report = inspect_readiness(ready_project, task_id=ulid(10))
    assert report.ready
    assert {warning.code for warning in report.warnings} >= {
        "few_positive_examples",
        "few_source_groups",
    }

    version, _ = freeze_dataset(
        ready_project,
        dataset_version_id=ulid(50),
        task_id=ulid(10),
        created_at=NOW,
    )
    assert version.version_number == 1
    assert {item.split for item in version.items} == {"train", "validation"}
    group_splits = {item.source_group_id: item.split for item in version.items}
    assert len(group_splits) == 2
    frozen = version.items[0].annotations[0]

    edit_annotation(
        ready_project,
        annotation_id=frozen.annotation_id,
        revision_id=ulid(60),
        concept_id=ulid(20),
        bbox=bbox(0.6),
        created_by="user",
        created_at=NOW + timedelta(seconds=1),
    )
    stored = ready_project.dataset_versions.get(version.dataset_version_id)
    assert stored.items[0].annotations[0].revision_id == frozen.revision_id
    assert stored.items[0].annotations[0].bbox == frozen.bbox


def test_new_concept_never_turns_old_media_into_implicit_negatives(ready_project):
    add_concept(
        ready_project,
        concept_id=ulid(21),
        task_id=ulid(10),
        display_name="B",
        created_at=NOW,
    )

    report = inspect_readiness(ready_project, task_id=ulid(10))

    unverified = [issue for issue in report.blockers if issue.code == "unverified_coverage"]
    assert len(unverified) == 2
    assert {issue.concept_id for issue in unverified} == {ulid(21)}
    with pytest.raises(DatasetNotReadyError) as caught:
        freeze_dataset(
            ready_project,
            dataset_version_id=ulid(51),
            task_id=ulid(10),
            created_at=NOW,
        )
    assert not caught.value.report.ready

    selected_a, _ = freeze_dataset(
        ready_project,
        dataset_version_id=ulid(52),
        task_id=ulid(10),
        concept_ids=(ulid(20),),
        created_at=NOW,
    )
    assert selected_a.concept_ids == (ulid(20),)


def test_source_group_split_is_never_leaked(ready_project):
    assignment = ready_project.assignments.get(ulid(10), sha(2))
    assert assignment is not None
    ready_project.db.execute(
        "UPDATE media_assignments SET source_group_id = ?, json = json_set(json,"
        " '$.source_group_id', ?) WHERE task_id = ? AND media_hash = ?",
        ("source-1", "source-1", ulid(10), sha(2)),
    )

    report = inspect_readiness(ready_project, task_id=ulid(10))

    assert "insufficient_source_groups" in {issue.code for issue in report.blockers}
