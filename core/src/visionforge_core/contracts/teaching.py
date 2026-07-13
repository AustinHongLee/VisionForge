"""R3 教學領域契約：一個 Project 內，以 Task 與 Concept 建立可重放真相。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from visionforge_core.contracts.claims import (
    SCHEMA_VERSION,
    BBox,
    Sha256,
    StrictModel,
    Ulid,
    _require_tz,
)


class TaskRecord(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    task_id: Ulid
    name: str = Field(min_length=1, max_length=128)
    kind: Literal["detect"] = "detect"
    created_at: datetime

    _tz = field_validator("created_at")(_require_tz)


class ConceptDefinition(StrictModel):
    """概念身分只在所屬 Task 內有意義，不再使用全專案隱式類別表。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    concept_id: Ulid
    task_id: Ulid
    display_name: str = Field(min_length=1, max_length=128)
    aliases: tuple[str, ...] = ()
    created_at: datetime

    _tz = field_validator("created_at")(_require_tz)

    @field_validator("aliases")
    @classmethod
    def _valid_aliases(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(alias.strip() for alias in value)
        if any(not alias or len(alias) > 128 for alias in cleaned):
            raise ValueError("alias 必須是 1–128 字元")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("alias 不得重複")
        return cleaned


class MediaAssignment(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    task_id: Ulid
    media_hash: Sha256
    source_group_id: str = Field(min_length=1, max_length=256)
    assigned_at: datetime

    _tz = field_validator("assigned_at")(_require_tz)


class CoverageState(str, Enum):
    unverified = "unverified"
    verified_complete = "verified_complete"
    verified_absent = "verified_absent"


class CoverageRecord(StrictModel):
    """一張圖對一個 Concept 的查核狀態；absence 的唯一權威來源。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    task_id: Ulid
    media_hash: Sha256
    concept_id: Ulid
    state: CoverageState = CoverageState.unverified
    reviewer: str | None = Field(default=None, min_length=1, max_length=256)
    verified_at: datetime | None = None

    @model_validator(mode="after")
    def _verification_metadata(self) -> CoverageRecord:
        verified = self.state is not CoverageState.unverified
        if verified != (self.reviewer is not None and self.verified_at is not None):
            raise ValueError("已驗證 Coverage 必須同時記載 reviewer 與 verified_at")
        if self.verified_at is not None:
            _require_tz(self.verified_at)
        return self


class AnnotationSource(str, Enum):
    manual = "manual"
    teacher_accepted = "teacher_accepted"
    teacher_edited = "teacher_edited"
    imported = "imported"


class AnnotationRevision(StrictModel):
    """標註的不可變修訂；刪除是 retracted revision，不抹去舊資料。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    revision_id: Ulid
    annotation_id: Ulid
    task_id: Ulid
    concept_id: Ulid
    media_hash: Sha256
    bbox: BBox | None
    source: AnnotationSource
    source_claim_ref: Ulid | None = None
    created_by: str = Field(min_length=1, max_length=256)
    created_at: datetime
    replaces_revision_id: Ulid | None = None
    status: Literal["active", "retracted"] = "active"

    _tz = field_validator("created_at")(_require_tz)

    @model_validator(mode="after")
    def _revision_invariants(self) -> AnnotationRevision:
        if self.status == "active" and self.bbox is None:
            raise ValueError("有效標註必須有 bbox")
        if self.status == "retracted" and self.bbox is not None:
            raise ValueError("撤回修訂不得帶 bbox")
        if self.source in {AnnotationSource.teacher_accepted, AnnotationSource.teacher_edited}:
            if self.source_claim_ref is None:
                raise ValueError("教師來源標註必須保留 source_claim_ref")
        return self


class ClaimTeachingContext(StrictModel):
    """把舊 Claim 的 provider 原話，可靠地綁回本次 Task/Concept。"""

    claim_id: Ulid
    task_id: Ulid
    concept_id: Ulid

