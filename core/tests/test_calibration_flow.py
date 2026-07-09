"""校準飛輪閉合測試（ADR-0010 #5）：已審→recalibrate→apply_latest。"""

from datetime import datetime, timezone

from visionforge_core.calibration import apply_latest, observations_from_reviews, recalibrate
from visionforge_core.contracts import (
    BBox,
    Claim,
    Concept,
    Confidence,
    MediaSubject,
    Producer,
    Reliability,
)
from visionforge_core.orchestrator import record_inference_run
from visionforge_core.review import approve, list_pending, reject
from visionforge_core.storage import create_project

NOW = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


def sha(n: int) -> str:
    return f"{n:064x}"


def ulid(n: int) -> str:
    return f"{n:026d}"


def claim(n: int, text: str, raw: float) -> Claim:
    return Claim(
        claim_id=ulid(n),
        geometry=BBox(x1=0.1, y1=0.1, x2=0.4, y2=0.4),
        concept=Concept(raw_text=text),
        confidence=Confidence(raw=raw),
    )


def seed_and_review(tmp_path):
    proj = create_project(tmp_path / "p", "q", ulid(1))
    record_inference_run(
        proj,
        subject=MediaSubject(media_hash=sha(1), width_px=800, height_px=600),
        producer=Producer(provider_id="fixture", provider_version="0.1.0", params_hash=sha(9)),
        task="detect",
        claims=(claim(100, "bolt", 0.9), claim(101, "bolt", 0.7), claim(102, "bolt", 0.3)),
        duration_ms=10,
        run_id=ulid(10), decision_id=ulid(20), cost_id=ulid(30), outcome_id=ulid(40),
        now=NOW,
    )
    pend = {p.claim.claim_id: p for p in list_pending(proj)}
    approve(proj, pend[ulid(100)], reviewer="a", reviewed_at=NOW,
            node_id=ulid(200), label_id=ulid(300), event_id=ulid(400))
    approve(proj, pend[ulid(101)], reviewer="a", reviewed_at=NOW,
            node_id=ulid(201), label_id=ulid(301), event_id=ulid(401))
    reject(proj, pend[ulid(102)], reviewer="a", reviewed_at=NOW, event_id=ulid(402))
    return proj


def recal(proj, **kw):
    params = dict(calibration_id=ulid(500), created_at=NOW, golden_manifest_ref=ulid(600),
                  n_min=1, n_high=2)
    params.update(kw)
    return recalibrate(proj, **params)


def test_observations_from_reviews(tmp_path):
    proj = seed_and_review(tmp_path)
    try:
        obs = observations_from_reviews(proj)
        assert len(obs) == 3
        by_correct = sorted(o.correct for o in obs)
        assert by_correct == [False, True, True]  # 2 approved, 1 rejected
        assert all(o.concept_key == "bolt" for o in obs)
    finally:
        proj.close()


def test_recalibrate_stores_snapshot_and_applies(tmp_path):
    proj = seed_and_review(tmp_path)
    try:
        # 校準前：apply_latest 無快照 → 原樣、reliability none
        before = apply_latest(proj, Confidence(raw=0.9), "bolt")
        assert before.reliability is Reliability.none and before.calibrated is None

        snap = recal(proj)
        assert snap is not None
        assert proj.calibrations.get_latest().calibration_id == ulid(500)

        # 校準後：bolt 有 3 觀測、n_high=2 → high；apply_latest 回填
        after = apply_latest(proj, Confidence(raw=0.9), "bolt")
        assert after.reliability is Reliability.high
        assert after.calibrated is not None
        assert after.calibration_ref == ulid(500)
    finally:
        proj.close()


def test_recalibrate_no_reviews_returns_none(tmp_path):
    proj = create_project(tmp_path / "empty", "q", ulid(1))
    try:
        assert recal(proj) is None
        assert proj.calibrations.get_latest() is None
    finally:
        proj.close()
