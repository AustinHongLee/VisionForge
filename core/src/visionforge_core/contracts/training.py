"""R3 資料凍結、訓練、模型與評估契約。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from visionforge_core.contracts.claims import (
    SCHEMA_VERSION,
    BBox,
    Sha256,
    StrictModel,
    Ulid,
    UnitFloat,
    _require_tz,
)
from visionforge_core.contracts.teaching import AnnotationSource


class ClassMapEntry(StrictModel):
    concept_id: Ulid
    class_index: int = Field(ge=0)
    display_name: str = Field(min_length=1, max_length=128)


class CoverageSnapshot(StrictModel):
    concept_id: Ulid
    state: Literal["verified_complete", "verified_absent"]


class DatasetAnnotation(StrictModel):
    annotation_id: Ulid
    revision_id: Ulid
    concept_id: Ulid
    bbox: BBox
    source: AnnotationSource
    source_claim_ref: Ulid | None = None


class DatasetItem(StrictModel):
    media_hash: Sha256
    source_group_id: str = Field(min_length=1, max_length=256)
    split: Literal["train", "validation"]
    coverage: tuple[CoverageSnapshot, ...]
    annotations: tuple[DatasetAnnotation, ...]


class DatasetVersion(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    dataset_version_id: Ulid
    version_number: int = Field(ge=1)
    task_id: Ulid
    concept_ids: tuple[Ulid, ...] = Field(min_length=1)
    class_map: tuple[ClassMapEntry, ...] = Field(min_length=1)
    items: tuple[DatasetItem, ...] = Field(min_length=2)
    created_at: datetime
    parent_ref: Ulid | None = None

    _tz = field_validator("created_at")(_require_tz)

    @model_validator(mode="after")
    def _version_invariants(self) -> DatasetVersion:
        if len(set(self.concept_ids)) != len(self.concept_ids):
            raise ValueError("DatasetVersion 的 Concept 不得重複")
        if {entry.concept_id for entry in self.class_map} != set(self.concept_ids):
            raise ValueError("class_map 必須完整對應 concept_ids")
        if {entry.class_index for entry in self.class_map} != set(range(len(self.class_map))):
            raise ValueError("class_map index 必須從 0 連續編號")
        if len({item.media_hash for item in self.items}) != len(self.items):
            raise ValueError("DatasetVersion 內不得有重複 media")
        if {item.split for item in self.items} != {"train", "validation"}:
            raise ValueError("DatasetVersion 必須同時有 train 與 validation")
        groups: dict[str, str] = {}
        for item in self.items:
            previous = groups.setdefault(item.source_group_id, item.split)
            if previous != item.split:
                raise ValueError("同一 source group 不得跨 train/validation")
        return self


class ReadinessIssue(StrictModel):
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=512)
    media_hash: Sha256 | None = None
    concept_id: Ulid | None = None


class ReadinessReport(StrictModel):
    blockers: tuple[ReadinessIssue, ...] = ()
    warnings: tuple[ReadinessIssue, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.blockers


class TrainingRecipe(StrictModel):
    input_size: int = Field(default=256, ge=64, le=2048)
    epochs: int = Field(default=20, ge=1, le=10_000)
    batch_size: int = Field(default=4, ge=1, le=1024)
    learning_rate: float = Field(default=0.001, gt=0, le=1)
    seed: int = Field(default=1337, ge=0, le=2**31 - 1)


class TrainingRun(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    training_run_id: Ulid
    dataset_version_id: Ulid
    task_id: Ulid
    trainer_id: Literal["visionforge_tiny_detector"] = "visionforge_tiny_detector"
    trainer_version: str = Field(min_length=1, max_length=64)
    recipe: TrainingRecipe
    created_at: datetime
    retry_of: Ulid | None = None

    _tz = field_validator("created_at")(_require_tz)


TrainingStatus = Literal[
    "queued", "running", "succeeded", "failed", "cancelled", "interrupted"
]


class TrainingRunEvent(StrictModel):
    event_id: Ulid
    training_run_id: Ulid
    status: TrainingStatus
    at: datetime
    progress: UnitFloat | None = None
    message: str = Field(default="", max_length=512)
    technical_detail: str = Field(default="", max_length=4096)

    _tz = field_validator("at")(_require_tz)


class ModelArtifact(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    artifact_id: Ulid
    artifact_hash: Sha256
    task_id: Ulid
    dataset_version_id: Ulid
    training_run_id: Ulid
    relative_path: str = Field(min_length=1, max_length=1024)
    class_map: tuple[ClassMapEntry, ...]
    input_size: int = Field(ge=64, le=2048)
    confidence_threshold: UnitFloat = 0.35
    created_at: datetime

    _tz = field_validator("created_at")(_require_tz)


class EvaluationMetric(StrictModel):
    name: Literal["precision", "recall", "mean_iou"]
    value: UnitFloat


class EvaluationError(StrictModel):
    media_hash: Sha256
    kind: Literal["missed", "false_positive", "localization", "classification"]
    concept_id: Ulid
    expected_bbox: BBox | None = None
    predicted_bbox: BBox | None = None
    confidence: UnitFloat | None = None


class EvaluationReport(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    evaluation_id: Ulid
    artifact_id: Ulid
    dataset_version_id: Ulid
    validation_media_hashes: tuple[Sha256, ...] = Field(min_length=1)
    metrics: tuple[EvaluationMetric, ...]
    errors: tuple[EvaluationError, ...] = ()
    created_at: datetime

    _tz = field_validator("created_at")(_require_tz)


class EvaluationFeedback(StrictModel):
    feedback_id: Ulid
    evaluation_id: Ulid
    artifact_id: Ulid
    task_id: Ulid
    media_hash: Sha256
    concept_id: Ulid
    created_at: datetime

    _tz = field_validator("created_at")(_require_tz)


class ModelPrediction(StrictModel):
    concept_id: Ulid
    display_name: str = Field(min_length=1, max_length=128)
    bbox: BBox
    confidence: UnitFloat
