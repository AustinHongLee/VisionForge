"""校準飛輪閉合（ADR-0010 #5）：已審結果 → 校準 → 存快照 → 回填信賴度。

觀測來源＝已審 claim：approve/edit_approved＝correct、rejected＝incorrect。
（最小骨架用全部已審結果；限縮到黃金集子集是後續精修。）純 core、無時鐘/隨機——
calibration_id、created_at、golden_manifest_ref 由呼叫端注入（A5）。
"""

from __future__ import annotations

from datetime import datetime

from visionforge_core.calibration.engine import (
    CalibrationObservation,
    apply_calibration,
    calibrate,
)
from visionforge_core.contracts import CalibrationSnapshot, Confidence
from visionforge_core.storage import Project

_APPROVED = frozenset({"approved", "edited_approved"})


def observations_from_reviews(project: Project) -> list[CalibrationObservation]:
    """把已審 claim 轉成 (concept_key, raw, correct) 觀測。"""
    return [
        CalibrationObservation(
            concept_key=claim.concept.raw_text,
            raw=claim.confidence.raw,
            correct=to_status in _APPROVED,
        )
        for claim, to_status in project.runs.iter_reviewed()
    ]


def recalibrate(
    project: Project,
    *,
    calibration_id: str,
    created_at: datetime,
    golden_manifest_ref: str,
    precision_target: float = 0.95,
    prior_strength: float = 50.0,
    n_min: int = 30,
    n_high: int = 200,
) -> CalibrationSnapshot | None:
    """由已審結果重算校準並存為快照；無觀測則回 None（不存空快照）。"""
    observations = observations_from_reviews(project)
    if not observations:
        return None
    snapshot = calibrate(
        observations,
        calibration_id=calibration_id,
        created_at=created_at,
        golden_manifest_ref=golden_manifest_ref,
        precision_target=precision_target,
        prior_strength=prior_strength,
        n_min=n_min,
        n_high=n_high,
    )
    project.calibrations.append(snapshot)
    return snapshot


def apply_latest(project: Project, confidence: Confidence, concept_key: str) -> Confidence:
    """用最新快照回填 calibrated／reliability；尚無快照則原樣回（reliability 維持 none）。"""
    snapshot = project.calibrations.get_latest()
    if snapshot is None:
        return confidence
    return apply_calibration(confidence, snapshot, concept_key)
