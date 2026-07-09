"""最小 Orchestrator 測試（ADR-0010 #1）：一次調用完整入帳（D3/D4）。"""

from datetime import datetime, timezone

from visionforge_core.contracts import (
    BBox,
    Claim,
    Concept,
    Confidence,
    MediaSubject,
    Producer,
)
from visionforge_core.orchestrator import record_inference_run
from visionforge_core.storage import create_project

NOW = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


def sha(n: int) -> str:
    return f"{n:064x}"


def ulid(n: int) -> str:
    return f"{n:026d}"


def make_subject() -> MediaSubject:
    return MediaSubject(media_hash=sha(1), width_px=1920, height_px=1080)


def make_producer() -> Producer:
    return Producer(provider_id="fixture", provider_version="0.1.0", params_hash=sha(9))


def make_claim(n: int) -> Claim:
    return Claim(
        claim_id=ulid(n),
        geometry=BBox(x1=0.1, y1=0.1, x2=0.5, y2=0.5),
        concept=Concept(raw_text="bolt"),
        confidence=Confidence(raw=0.8),
    )


def record(project, **kw):
    params = dict(
        subject=make_subject(), producer=make_producer(), task="detect",
        claims=(make_claim(100),), duration_ms=42,
        run_id=ulid(10), decision_id=ulid(20), cost_id=ulid(30), outcome_id=ulid(40),
        now=NOW,
    )
    params.update(kw)
    return record_inference_run(project, **params)


def test_records_decision_cost_run_outcome(tmp_path):
    proj = create_project(tmp_path / "p", "q", ulid(1))
    try:
        run = record(proj)
        # Run + claims
        assert proj.runs.get(ulid(10)).run_id == ulid(10)
        assert proj.runs.get_claim(ulid(100)).concept.raw_text == "bolt"
        assert run.cost_ref == ulid(30) and run.decision_ref == ulid(20)
        # Decision（invoke_provider，target 帶版本）
        d = proj.decisions.get(ulid(20))
        assert d.kind == "invoke_provider"
        assert d.choice.target == "fixture@0.1.0"
        assert d.choice.reason_code == "only_capable"
        # Cost（actual，掛在 run 上）
        costs = proj.costs.iter_by_subject("run", ulid(10))
        assert len(costs) == 1 and costs[0].phase == "actual"
        # Outcome（success）
        outcomes = proj.decisions.iter_outcomes(ulid(20))
        assert len(outcomes) == 1 and outcomes[0].status == "success"
    finally:
        proj.close()


def test_deterministic_same_inputs(tmp_path):
    a = create_project(tmp_path / "a", "q", ulid(1))
    b = create_project(tmp_path / "b", "q", ulid(1))
    try:
        record(a)
        record(b)
        assert a.runs.get(ulid(10)).model_dump() == b.runs.get(ulid(10)).model_dump()
        assert a.decisions.get(ulid(20)).model_dump() == b.decisions.get(ulid(20)).model_dump()
    finally:
        a.close()
        b.close()
