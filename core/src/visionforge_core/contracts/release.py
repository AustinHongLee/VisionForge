"""CapabilityRelease：唯一對使用者呈現 v1/v2 的不可變可攜能力版本。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from visionforge_core.contracts.claims import (
    SCHEMA_VERSION,
    Sha256,
    StrictModel,
    Ulid,
    _require_tz,
)


class CapabilityRelease(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    release_id: Ulid
    version_number: int = Field(ge=1)
    task_id: Ulid
    artifact_ids: tuple[Ulid, ...] = Field(min_length=1)
    archive_hash: Sha256
    manifest_hash: Sha256
    relative_path: str = Field(min_length=1, max_length=1024)
    created_at: datetime
    parent_ref: Ulid | None = None

    _tz = field_validator("created_at")(_require_tz)
