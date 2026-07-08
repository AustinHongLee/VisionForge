"""信心校準引擎（ADR-0007）：全域先驗＋逐類收縮。

純函數、無 IO、無時鐘、無隨機——給定同一輸入與參數，輸出逐位元一致（A5）。
時間戳與 calibration_id 由呼叫端傳入，引擎不碰系統時鐘。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from visionforge_core.contracts.calibration import (
    CALIBRATION_METHOD,
    CalibrationMapping,
    CalibrationSnapshot,
    ClassCalibration,
    MappingPoint,
)
from visionforge_core.contracts.claims import Confidence, Reliability


@dataclass(frozen=True)
class CalibrationObservation:
    """一筆帶標籤的觀測：某概念的一個 provider 草稿，raw 信心與是否正確。

    由 orchestrator 從黃金集×claims join 而來；引擎只吃這個乾淨形狀。
    """

    concept_key: str
    raw: float
    correct: bool


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _threshold_at_precision(
    samples: Sequence[tuple[float, bool]], precision_target: float
) -> float:
    """最低門檻 t，使 {raw>=t} 的精確率 >= target 且由高門檻連續達標；無解回 1.0（全拒）。

    由高到低掃描候選門檻，維持連續達標區段的最低點；一旦往下跌破 target 即止（保守）。
    """
    if not samples:
        return 1.0
    candidates = sorted({raw for raw, _ in samples}, reverse=True)
    best = 1.0
    passed_any = False
    for t in candidates:
        passing = [(r, c) for r, c in samples if r >= t]
        total = len(passing)
        if total == 0:
            continue
        correct = sum(1 for _, c in passing if c)
        if correct / total >= precision_target:
            best = t
            passed_any = True
        elif passed_any:
            break  # 連續達標區段已結束，不再往下放寬
    return _clamp01(best)


def _isotonic_mapping(samples: Sequence[tuple[float, bool]]) -> CalibrationMapping:
    """對 (raw, correct) 做等滲回歸（PAV），得單調非遞減的 raw→P(correct|raw) 階梯映射。"""
    ordered = sorted(samples, key=lambda s: s[0])
    points = [(raw, 1.0 if correct else 0.0) for raw, correct in ordered]
    # blocks：[值總和, 樣本數, 區段起始 raw]
    blocks: list[list[float]] = []
    for raw, y in points:
        blocks.append([y, 1.0, raw])
        while len(blocks) >= 2 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            s2, c2, _lo2 = blocks.pop()
            s1, c1, lo1 = blocks.pop()
            blocks.append([s1 + s2, c1 + c2, lo1])
    breakpoints: list[MappingPoint] = []
    for total, count, lo_raw in blocks:
        value = _clamp01(total / count)
        breakpoints.append(MappingPoint(raw=_clamp01(lo_raw), calibrated=value))
    return CalibrationMapping(points=tuple(breakpoints))


def _apply_mapping(mapping: CalibrationMapping, raw: float) -> float:
    """階梯函數：取最後一個 raw <= 查詢值的斷點；查詢值低於首斷點則用首值。"""
    calibrated = mapping.points[0].calibrated
    for point in mapping.points:
        if raw >= point.raw:
            calibrated = point.calibrated
        else:
            break
    return _clamp01(calibrated)


def _reliability_for(n: int, n_min: int, n_high: int) -> Reliability:
    if n < n_min:
        return Reliability.none
    if n < n_high:
        return Reliability.low
    return Reliability.high


def calibrate(
    observations: Sequence[CalibrationObservation],
    *,
    calibration_id: str,
    created_at: datetime,
    golden_manifest_ref: str,
    precision_target: float = 0.95,
    prior_strength: float = 50.0,
    n_min: int = 30,
    n_high: int = 200,
) -> CalibrationSnapshot:
    """由帶標籤觀測產生校準快照：全域門檻 + 逐類收縮門檻 + 信賴度分級。"""
    all_samples = [(o.raw, o.correct) for o in observations]
    t_global = _threshold_at_precision(all_samples, precision_target)

    by_class: dict[str, list[tuple[float, bool]]] = {}
    for o in observations:
        by_class.setdefault(o.concept_key, []).append((o.raw, o.correct))

    classes: list[ClassCalibration] = []
    for key in sorted(by_class):  # 確定性排序
        samples = by_class[key]
        n = len(samples)
        lam = prior_strength / (prior_strength + n)
        reliability = _reliability_for(n, n_min, n_high)
        if reliability is Reliability.none:
            # 保守退路：退回全域門檻、不輸出映射、強制人審（R2 9.2）。
            threshold = t_global
            mapping = None
        else:
            t_raw = _threshold_at_precision(samples, precision_target)
            threshold = lam * t_global + (1.0 - lam) * t_raw
            mapping = _isotonic_mapping(samples)
        classes.append(
            ClassCalibration(
                concept_key=key,
                n_samples=n,
                threshold=_clamp01(threshold),
                shrinkage_weight=lam,
                reliability=reliability,
                mapping=mapping,
            )
        )

    return CalibrationSnapshot(
        calibration_id=calibration_id,
        created_at=created_at,
        method=CALIBRATION_METHOD,
        precision_target=_clamp01(precision_target),
        prior_strength=prior_strength,
        global_threshold=t_global,
        golden_manifest_ref=golden_manifest_ref,
        classes=tuple(classes),
    )


def apply_calibration(
    conf: Confidence, snapshot: CalibrationSnapshot, concept_key: str
) -> Confidence:
    """回填 calibrated／reliability／calibration_ref。

    未知類或 none 級 → 不輸出 calibrated、reliability=none（分流保守走人審）。
    """
    match = next((c for c in snapshot.classes if c.concept_key == concept_key), None)
    if match is None or match.reliability is Reliability.none or match.mapping is None:
        return Confidence(raw=conf.raw, reliability=Reliability.none)
    calibrated = _apply_mapping(match.mapping, conf.raw)
    return Confidence(
        raw=conf.raw,
        calibrated=calibrated,
        calibration_ref=snapshot.calibration_id,
        reliability=match.reliability,
    )
