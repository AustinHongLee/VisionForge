"""校準引擎測試（ADR-0007）：收縮、信賴度分級、確定性、映射單調、套用。"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from visionforge_core.calibration import CalibrationObservation, apply_calibration, calibrate
from visionforge_core.contracts import (
    CalibrationSnapshot,
    ClassCalibration,
    Confidence,
    Reliability,
)

NOW = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
CID = "0" * 26
GID = "1" * 26


def obs(key: str, raw: float, correct: bool) -> CalibrationObservation:
    return CalibrationObservation(concept_key=key, raw=raw, correct=correct)


def run(observations, **kw):
    params = dict(
        calibration_id=CID, created_at=NOW, golden_manifest_ref=GID,
        precision_target=0.95, prior_strength=50.0, n_min=2, n_high=4,
    )
    params.update(kw)
    return calibrate(observations, **params)


# ---- 確定性（A5）----

def test_deterministic_same_input_same_output():
    data = [obs("bolt", 0.9, True), obs("bolt", 0.4, False), obs("crack", 0.7, True)]
    assert run(data).model_dump() == run(list(reversed(data))).model_dump()


# ---- 信賴度分級（none/low/high 由有效樣本量）----

def test_reliability_bands():
    data = (
        [obs("few", 0.9, True)]                                   # n=1 < n_min → none
        + [obs("mid", 0.9, True), obs("mid", 0.8, True), obs("mid", 0.3, False)]  # n=3 → low
        + [obs("many", 0.9, True), obs("many", 0.85, True),
           obs("many", 0.8, True), obs("many", 0.2, False)]       # n=4 ≥ n_high → high
    )
    snap = run(data)
    by = {c.concept_key: c for c in snap.classes}
    assert by["few"].reliability is Reliability.none
    assert by["few"].mapping is None                 # none 不輸出映射
    assert by["few"].threshold == snap.global_threshold  # 退回保守全域門檻
    assert by["mid"].reliability is Reliability.low
    assert by["mid"].mapping is not None
    assert by["many"].reliability is Reliability.high


# ---- 收縮權重 λ = N0/(N0+n)----

def test_shrinkage_weight_formula():
    data = [obs("c", 0.9, True), obs("c", 0.8, True), obs("c", 0.3, False)]  # n=3
    snap = run(data, prior_strength=50.0)
    cc = snap.classes[0]
    assert cc.n_samples == 3
    assert cc.shrinkage_weight == pytest.approx(50.0 / 53.0)


# ---- 門檻＝達標精確率之最低連續門檻----

def test_global_threshold_at_precision():
    data = [obs("c", 0.9, True), obs("c", 0.8, True), obs("c", 0.3, False), obs("c", 0.2, False)]
    snap = run(data)
    assert snap.global_threshold == pytest.approx(0.8)


def test_no_threshold_meets_precision_rejects_all():
    data = [obs("c", 0.9, False), obs("c", 0.8, False)]  # 全錯 → 無門檻達標
    assert run(data).global_threshold == 1.0


def test_empty_observations():
    snap = run([])
    assert snap.global_threshold == 1.0
    assert snap.classes == ()


# ---- 等滲映射單調 + 套用----

def test_apply_high_class_sets_calibrated_and_ref():
    data = [
        obs("m", 0.95, True), obs("m", 0.9, True), obs("m", 0.85, True),
        obs("m", 0.6, True), obs("m", 0.4, False), obs("m", 0.2, False),
    ]  # n=6 ≥ n_high → high
    snap = run(data)
    out = apply_calibration(Confidence(raw=0.9), snap, "m")
    assert out.reliability is Reliability.high
    assert out.calibrated is not None
    assert out.calibration_ref == CID
    # 單調：高 raw 的校準值 ≥ 低 raw
    low = apply_calibration(Confidence(raw=0.3), snap, "m")
    assert out.calibrated >= low.calibrated


def test_apply_unknown_or_none_class_is_conservative():
    snap = run([obs("only", 0.9, True)])  # 'only' n=1 → none
    unknown = apply_calibration(Confidence(raw=0.9), snap, "not-present")
    assert unknown.calibrated is None
    assert unknown.reliability is Reliability.none
    none_cls = apply_calibration(Confidence(raw=0.9), snap, "only")
    assert none_cls.calibrated is None
    assert none_cls.reliability is Reliability.none


# ---- 契約不變量----

def test_snapshot_rejects_duplicate_class_keys():
    dup = ClassCalibration(concept_key="x", n_samples=0, threshold=0.5,
                           shrinkage_weight=1.0, reliability=Reliability.none)
    with pytest.raises(ValidationError):
        CalibrationSnapshot(
            calibration_id=CID, created_at=NOW, precision_target=0.95,
            prior_strength=50.0, global_threshold=0.5, golden_manifest_ref=GID,
            classes=(dup, dup),
        )


def test_none_reliability_forbids_mapping_and_high_requires_it():
    from visionforge_core.contracts import CalibrationMapping, MappingPoint
    m = CalibrationMapping(points=(MappingPoint(raw=0.0, calibrated=0.5),))
    with pytest.raises(ValidationError):  # none 不得帶映射
        ClassCalibration(concept_key="x", n_samples=1, threshold=0.5,
                         shrinkage_weight=1.0, reliability=Reliability.none, mapping=m)
    with pytest.raises(ValidationError):  # high 必須帶映射
        ClassCalibration(concept_key="x", n_samples=9, threshold=0.5,
                         shrinkage_weight=0.1, reliability=Reliability.high, mapping=None)
