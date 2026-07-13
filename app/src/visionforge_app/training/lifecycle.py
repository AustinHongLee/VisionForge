"""TrainingRun 只增事件的狀態機；任何 attempt 與失敗都不覆寫。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from visionforge_core.contracts import (
    TrainingRecipe,
    TrainingRun,
    TrainingRunEvent,
    TrainingStatus,
)
from visionforge_core.storage import Project
from visionforge_core.storage.errors import ConflictError

_TERMINAL = frozenset({"succeeded", "failed", "cancelled", "interrupted"})
_ALLOWED: dict[str, frozenset[str]] = {
    "queued": frozenset({"running", "failed", "cancelled", "interrupted"}),
    "running": frozenset({"succeeded", "failed", "cancelled", "interrupted"}),
}


def create_training_run(
    project: Project,
    *,
    training_run_id: str,
    dataset_version_id: str,
    trainer_version: str,
    recipe: TrainingRecipe,
    created_at: datetime,
    queued_event_id: str,
    retry_of: str | None = None,
) -> TrainingRun:
    dataset = project.dataset_versions.get(dataset_version_id)
    if retry_of is not None:
        original = project.training_runs.get(retry_of)
        if original.dataset_version_id != dataset_version_id:
            raise ConflictError("重試必須使用原 TrainingRun 的同一 DatasetVersion")
    run = TrainingRun(
        training_run_id=training_run_id,
        dataset_version_id=dataset_version_id,
        task_id=dataset.task_id,
        trainer_version=trainer_version,
        recipe=recipe,
        created_at=created_at,
        retry_of=retry_of,
    )
    event = TrainingRunEvent(
        event_id=queued_event_id,
        training_run_id=training_run_id,
        status="queued",
        at=created_at,
        progress=0,
        message="已排入本機訓練",
    )
    with project.db.transaction():
        project.training_runs.append(run)
        project.training_runs.append_event(event)
    return run


def append_training_event(
    project: Project,
    *,
    training_run_id: str,
    event_id: str,
    status: TrainingStatus,
    at: datetime,
    progress: float | None = None,
    message: str = "",
    technical_detail: str = "",
) -> TrainingRunEvent:
    project.training_runs.get(training_run_id)
    previous = project.training_runs.latest_event(training_run_id)
    if previous.status in _TERMINAL:
        raise ConflictError(f"TrainingRun 已終止於 {previous.status}")
    if status not in _ALLOWED.get(previous.status, frozenset()):
        if not (previous.status == "running" and status == "running"):
            raise ConflictError(f"不合法的訓練狀態轉移：{previous.status} → {status}")
    event = TrainingRunEvent(
        event_id=event_id,
        training_run_id=training_run_id,
        status=status,
        at=at,
        progress=progress,
        message=message,
        technical_detail=technical_detail,
    )
    project.training_runs.append_event(event)
    return event


def interrupt_orphaned_runs(
    project: Project,
    *,
    now: datetime,
    id_factory: Callable[[], str],
) -> list[TrainingRunEvent]:
    events: list[TrainingRunEvent] = []
    for status in ("queued", "running"):
        for run in project.training_runs.list_with_status(status):
            events.append(
                append_training_event(
                    project,
                    training_run_id=run.training_run_id,
                    event_id=id_factory(),
                    status="interrupted",
                    at=now,
                    message="Sidecar 重啟，前次訓練已中斷；可安全重試",
                )
            )
    return events
