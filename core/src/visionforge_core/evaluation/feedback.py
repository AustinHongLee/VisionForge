"""把 frozen validation 錯誤顯式回流，並從未來 validation 除役。"""

from __future__ import annotations

from datetime import datetime

from visionforge_core.contracts import (
    CoverageRecord,
    EvaluationFeedback,
)
from visionforge_core.storage import Project
from visionforge_core.storage.errors import NotFoundError


def send_error_to_teaching(
    project: Project,
    *,
    evaluation_id: str,
    error_index: int,
    feedback_id: str,
    created_at: datetime,
) -> EvaluationFeedback:
    report = project.evaluations.get(evaluation_id)
    if error_index < 0 or error_index >= len(report.errors):
        raise NotFoundError("evaluation error 不存在")
    error = report.errors[error_index]
    artifact = project.model_artifacts.get(report.artifact_id)
    assignment = project.assignments.get(artifact.task_id, error.media_hash)
    if assignment is None:
        raise NotFoundError("evaluation media 已不在原 Task")
    feedback = EvaluationFeedback(
        feedback_id=feedback_id,
        evaluation_id=evaluation_id,
        artifact_id=artifact.artifact_id,
        task_id=artifact.task_id,
        media_hash=error.media_hash,
        concept_id=error.concept_id,
        created_at=created_at,
    )
    with project.db.transaction():
        project.evaluation_feedback.append(feedback)
        project.coverage.set(
            CoverageRecord(
                task_id=artifact.task_id,
                media_hash=error.media_hash,
                concept_id=error.concept_id,
            )
        )
    return feedback
