"""Slice 2：TrainingRun child worker、成功註冊與失敗不產 Artifact。"""

from datetime import datetime, timezone
from importlib.util import find_spec
from io import BytesIO

import pytest
from PIL import Image
from visionforge_app.importer import import_media
from visionforge_app.training import create_training_run, interrupt_orphaned_runs
from visionforge_app.training import worker as worker_module
from visionforge_app.training.tiny_detector import load_and_predict
from visionforge_app.training.worker import run_worker
from visionforge_core.contracts import (
    BBox,
    CoverageState,
    EvaluationError,
    EvaluationReport,
    MediaSource,
    TrainingRecipe,
)
from visionforge_core.dataset import freeze_dataset
from visionforge_core.evaluation import send_error_to_teaching
from visionforge_core.storage import create_project, open_project
from visionforge_core.teaching import (
    add_annotation,
    add_concept,
    add_task,
    assign_media,
    set_coverage,
)

NOW = datetime(2026, 7, 13, 3, 0, tzinfo=timezone.utc)


def ulid(n: int) -> str:
    return f"{n:026d}"


def image_bytes(color: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 32), color).save(output, format="PNG")
    return output.getvalue()


@pytest.fixture()
def training_project(tmp_path):
    root = tmp_path / "project"
    project = create_project(root, "train", ulid(1))
    add_task(project, task_id=ulid(10), name="detect", created_at=NOW)
    add_concept(
        project,
        concept_id=ulid(20),
        task_id=ulid(10),
        display_name="A",
        created_at=NOW,
    )
    for index, color in enumerate(((255, 0, 0), (0, 255, 0)), start=1):
        outcome = import_media(
            project,
            image_bytes(color),
            MediaSource(kind="file", detail=f"{index}.png"),
        )
        assign_media(
            project,
            task_id=ulid(10),
            media_hash=outcome.media_hash,
            source_group_id=f"group-{index}",
            assigned_at=NOW,
        )
        add_annotation(
            project,
            revision_id=ulid(30 + index),
            annotation_id=ulid(40 + index),
            task_id=ulid(10),
            media_hash=outcome.media_hash,
            concept_id=ulid(20),
            bbox=BBox(x1=0.2, y1=0.2, x2=0.6, y2=0.6),
            created_by="user",
            created_at=NOW,
        )
        set_coverage(
            project,
            task_id=ulid(10),
            media_hash=outcome.media_hash,
            concept_id=ulid(20),
            state=CoverageState.verified_complete,
            reviewer="user",
            verified_at=NOW,
        )
    version, _ = freeze_dataset(
        project,
        dataset_version_id=ulid(50),
        task_id=ulid(10),
        created_at=NOW,
    )
    project.close()
    return root, version


def create_run(root, run_id: str, *, input_size: int = 256):
    with open_project(root) as project:
        return create_training_run(
            project,
            training_run_id=run_id,
            dataset_version_id=ulid(50),
            trainer_version="1.0.0",
            recipe=TrainingRecipe(epochs=1, input_size=input_size),
            created_at=NOW,
            queued_event_id=ulid(int(run_id) + 1),
        )


def test_fixture_worker_registers_artifact_evaluation_and_success(
    training_project, monkeypatch
):
    root, version = training_project
    create_run(root, ulid(60))
    monkeypatch.setenv("VISIONFORGE_TRAINER_FIXTURE", "1")

    run_worker(root, ulid(60))

    with open_project(root) as project:
        latest = project.training_runs.latest_event(ulid(60))
        artifact = project.model_artifacts.by_run(ulid(60))
        assert latest.status == "succeeded"
        assert artifact is not None
        assert (root / artifact.relative_path).is_file()
        report = project.evaluations.latest_for_artifact(artifact.artifact_id)
        assert report is not None
        assert report.dataset_version_id == version.dataset_version_id
        assert report.validation_media_hashes


def test_failed_worker_never_registers_artifact(training_project, monkeypatch):
    root, _ = training_project
    create_run(root, ulid(70))
    monkeypatch.delenv("VISIONFORGE_TRAINER_FIXTURE", raising=False)

    def fail(*_args, **_kwargs):
        raise RuntimeError("simulated trainer crash")

    monkeypatch.setattr(worker_module, "train_and_evaluate", fail)
    with pytest.raises(RuntimeError, match="simulated trainer crash"):
        run_worker(root, ulid(70))

    with open_project(root) as project:
        assert project.training_runs.latest_event(ulid(70)).status == "failed"
        assert project.model_artifacts.by_run(ulid(70)) is None


@pytest.mark.skipif(find_spec("torch") is None, reason="training optional dependency not installed")
def test_real_tiny_detector_trains_saves_and_reloads(training_project, monkeypatch):
    root, _ = training_project
    create_run(root, ulid(75), input_size=64)
    monkeypatch.delenv("VISIONFORGE_TRAINER_FIXTURE", raising=False)

    run_worker(root, ulid(75))

    with open_project(root) as project:
        artifact = project.model_artifacts.by_run(ulid(75))
        assert artifact is not None
        sample = project.dataset_versions.get(ulid(50)).items[0]
        blob = project.blobs.find(sample.media_hash)
        assert blob is not None
        predictions = load_and_predict(
            root / artifact.relative_path,
            blob.read_bytes(),
            threshold=artifact.confidence_threshold,
        )
        assert isinstance(predictions, tuple)
        assert project.training_runs.latest_event(ulid(75)).status == "succeeded"


def test_restart_marks_queued_attempt_interrupted(training_project):
    root, _ = training_project
    create_run(root, ulid(80))
    ids = iter((ulid(82), ulid(83)))

    with open_project(root) as project:
        events = interrupt_orphaned_runs(project, now=NOW, id_factory=lambda: next(ids))
        assert len(events) == 1
        assert events[0].status == "interrupted"
        assert project.model_artifacts.by_run(ulid(80)) is None


def test_validation_feedback_is_unverified_then_forced_out_of_future_validation(
    training_project, monkeypatch
):
    root, version = training_project
    create_run(root, ulid(90))
    monkeypatch.setenv("VISIONFORGE_TRAINER_FIXTURE", "1")
    run_worker(root, ulid(90))

    with open_project(root) as project:
        artifact = project.model_artifacts.by_run(ulid(90))
        assert artifact is not None
        validation_item = next(item for item in version.items if item.split == "validation")
        report = EvaluationReport(
            evaluation_id=ulid(92),
            artifact_id=artifact.artifact_id,
            dataset_version_id=version.dataset_version_id,
            validation_media_hashes=(validation_item.media_hash,),
            metrics=(),
            errors=(
                EvaluationError(
                    media_hash=validation_item.media_hash,
                    kind="missed",
                    concept_id=ulid(20),
                    expected_bbox=validation_item.annotations[0].bbox,
                ),
            ),
            created_at=NOW,
        )
        project.evaluations.append(report)
        send_error_to_teaching(
            project,
            evaluation_id=report.evaluation_id,
            error_index=0,
            feedback_id=ulid(93),
            created_at=NOW,
        )
        assert project.coverage.get(
            ulid(10), validation_item.media_hash, ulid(20)
        ).state is CoverageState.unverified
        set_coverage(
            project,
            task_id=ulid(10),
            media_hash=validation_item.media_hash,
            concept_id=ulid(20),
            state=CoverageState.verified_complete,
            reviewer="user",
            verified_at=NOW,
        )
        next_version, _ = freeze_dataset(
            project,
            dataset_version_id=ulid(94),
            task_id=ulid(10),
            created_at=NOW,
        )
        feedback_item = next(
            item for item in next_version.items if item.media_hash == validation_item.media_hash
        )
        assert feedback_item.split == "train"
