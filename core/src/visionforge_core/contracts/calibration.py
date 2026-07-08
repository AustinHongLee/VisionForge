"""校準快照契約（ADR-0007）。

校準引擎的產物：不可變、可審計、以 ULID 定址的逐類校準快照。
分流引擎只讀 Confidence.calibrated；本快照是 calibrated／reliability 的唯一合法來源，
且 reliability 必有快照背書（P5：不可驗證的能力視同不存在）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from visionforge_core.contracts.claims import (
    SCHEMA_VERSION,
    Reliability,
    StrictModel,
    Ulid,
    UnitFloat,
    _require_tz,
)

# 方法釘版：改演算法＝出新版本字串（A5 確定性、可回溯）。
CALIBRATION_METHOD = "shrinkage_eb_v1"


class MappingPoint(StrictModel):
    """等滲回歸斷點：raw 門檻 → 校準後信心（P(correct|raw) 的單調估計）。"""

    raw: UnitFloat
    calibrated: UnitFloat


class CalibrationMapping(StrictModel):
    """raw→calibrated 的單調階梯映射；points 依 raw 遞增、calibrated 非遞減。"""

    points: tuple[MappingPoint, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _monotone(self) -> CalibrationMapping:
        prev_raw = -1.0
        prev_cal = -1.0
        for p in self.points:
            if p.raw < prev_raw:
                raise ValueError("mapping points 必須依 raw 遞增")
            if p.calibrated < prev_cal:
                raise ValueError("校準映射必須單調非遞減（等滲回歸不變量）")
            prev_raw = p.raw
            prev_cal = p.calibrated
        return self


class ClassCalibration(StrictModel):
    """逐類校準結果。none 級不輸出映射、退回保守全域門檻（R2 9.2）。"""

    concept_key: str = Field(min_length=1, max_length=512)
    n_samples: int = Field(ge=0)
    threshold: UnitFloat
    shrinkage_weight: float = Field(ge=0.0, le=1.0)  # λ_c：向全域先驗收縮的權重
    reliability: Reliability
    mapping: CalibrationMapping | None = None

    @model_validator(mode="after")
    def _reliability_mapping_invariant(self) -> ClassCalibration:
        if self.reliability is not Reliability.none and self.mapping is None:
            raise ValueError("low／high 信賴度必須附校準映射（P5）")
        if self.reliability is Reliability.none and self.mapping is not None:
            raise ValueError("none 信賴度不得輸出校準映射（保守退路）")
        return self


class CalibrationSnapshot(StrictModel):
    """一次校準的不可變快照；calibration_ref 指向它＝信賴度的可驗證背書。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    calibration_id: Ulid
    created_at: datetime
    method: Literal["shrinkage_eb_v1"] = CALIBRATION_METHOD
    precision_target: UnitFloat
    prior_strength: float = Field(gt=0.0)  # N0
    global_threshold: UnitFloat
    golden_manifest_ref: Ulid  # 血統：本次校準依據的黃金集版本
    classes: tuple[ClassCalibration, ...] = Field(default_factory=tuple)

    _tz = field_validator("created_at")(_require_tz)

    @model_validator(mode="after")
    def _unique_class_keys(self) -> CalibrationSnapshot:
        keys = [c.concept_key for c in self.classes]
        if len(keys) != len(set(keys)):
            raise ValueError("classes 的 concept_key 必須唯一")
        return self
