"""帳本 Schema v1.0 契約測試（ADR-0004）——帳本的規格，B1 的「誠實」由此定義。"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from visionforge_core.contracts import (
    CandidateProvider,
    CostAgent,
    CostEntry,
    CostMeasurement,
    DatasetVersionManifest,
    DecisionChoice,
    DecisionOutcome,
    DecisionRecord,
    GoldenSetEntry,
    InputRef,
    ManifestEntry,
    PolicyRef,
    ProvenanceSummary,
    ReviewEvent,
    ReviewStatus,
)

ULID_A = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
ULID_B = "01BX5ZZKBKACTAV9WEVGEMMVRZ"
SHA = "ab" * 32
SHA2 = "cd" * 32
NOW = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)


def make_decision(**overrides):
    base = dict(
        decision_id=ULID_A,
        at=NOW,
        kind="invoke_provider",
        policy=PolicyRef(policy_hash=SHA, policy_label="default-rules-v1"),
        inputs=(InputRef(kind="media", id=SHA),),
        candidates=(
            CandidateProvider(
                provider_id="grounding-dino",
                provider_version="1.5.1",
                capability_ok=True,
                audition_score=0.91,
            ),
        ),
        choice=DecisionChoice(target="grounding-dino@1.5.1", reason_code="audition_best"),
    )
    base.update(overrides)
    return DecisionRecord(**base)


def make_cost(**overrides):
    base = dict(
        cost_id=ULID_A,
        at=NOW,
        phase="actual",
        subject=InputRef(kind="run", id=ULID_B),
        agent=CostAgent(kind="provider", id="grounding-dino", version="1.5.1"),
        measurements=(CostMeasurement(unit="seconds", amount=Decimal("1.42")),),
        estimate_ref=ULID_B,
    )
    base.update(overrides)
    return CostEntry(**base)


# ---- Decision（D3/A6/A12） ----


def test_decision_roundtrip():
    d = make_decision()
    assert DecisionRecord.model_validate_json(d.model_dump_json()) == d


def test_unregistered_reason_code_rejected():
    with pytest.raises(ValidationError):
        DecisionChoice(target="x", reason_code="because_i_felt_like_it")


def test_invoke_provider_requires_candidates():
    with pytest.raises(ValidationError):
        make_decision(candidates=())


def test_human_override_requires_ref_and_human_actor():
    with pytest.raises(ValidationError):  # 缺 overrides_ref
        make_decision(kind="human_override", actor="李宗鴻", candidates=(),
                      choice=DecisionChoice(target="manual", reason_code="human_judgment"))
    with pytest.raises(ValidationError):  # actor 不是人
        make_decision(kind="human_override", overrides_ref=ULID_B, candidates=(),
                      choice=DecisionChoice(target="manual", reason_code="human_judgment"))
    ok = make_decision(kind="human_override", actor="李宗鴻", overrides_ref=ULID_B,
                       candidates=(),
                       choice=DecisionChoice(target="manual", reason_code="human_judgment"))
    assert ok.overrides_ref == ULID_B


def test_non_override_must_not_carry_overrides_ref():
    with pytest.raises(ValidationError):
        make_decision(overrides_ref=ULID_B)


def test_outcome_is_separate_append_record():
    o = DecisionOutcome(outcome_id=ULID_A, decision_ref=ULID_B, at=NOW, status="success",
                        produced_refs=(InputRef(kind="run", id=ULID_A),))
    assert DecisionOutcome.model_validate_json(o.model_dump_json()) == o


# ---- Cost（C1/C5/C6/D4/F3） ----


def test_cost_decimal_exact_roundtrip():
    """錢不進浮點數：0.000123 必須一分不差地回來。"""
    c = make_cost(measurements=(CostMeasurement(unit="usd", amount=Decimal("0.000123")),))
    restored = CostEntry.model_validate_json(c.model_dump_json())
    assert restored.measurements[0].amount == Decimal("0.000123")


def test_estimate_must_not_reference_estimate():
    with pytest.raises(ValidationError):
        make_cost(phase="estimate")  # base 帶 estimate_ref → 違規
    ok = make_cost(phase="estimate", estimate_ref=None)
    assert ok.phase == "estimate"


def test_human_review_time_is_priced():
    """C5：人工是最貴的 Provider，時間同樣入帳。"""
    c = make_cost(
        agent=CostAgent(kind="human", id="李宗鴻"),
        subject=InputRef(kind="review_event", id=ULID_B),
        measurements=(CostMeasurement(unit="seconds", amount=Decimal("35")),),
    )
    assert c.agent.kind == "human"


def test_provider_cost_requires_version():
    with pytest.raises(ValidationError):
        CostAgent(kind="provider", id="grounding-dino")


def test_negative_amount_rejected():
    with pytest.raises(ValidationError):
        CostMeasurement(unit="usd", amount=Decimal("-1"))


# ---- ReviewEvent（P4/D7/防線五） ----


def test_approval_must_produce_label():
    with pytest.raises(ValidationError):
        ReviewEvent(event_id=ULID_A, at=NOW, actor="李宗鴻", claim_ref=ULID_B,
                    from_status=ReviewStatus.queued_fast, to_status=ReviewStatus.approved)


def test_rejection_must_not_carry_label():
    with pytest.raises(ValidationError):
        ReviewEvent(event_id=ULID_A, at=NOW, actor="李宗鴻", claim_ref=ULID_B,
                    from_status=ReviewStatus.queued_detail, to_status=ReviewStatus.rejected,
                    label_ref=ULID_A)


def test_no_op_transition_rejected():
    with pytest.raises(ValidationError):
        ReviewEvent(event_id=ULID_A, at=NOW, actor="李宗鴻", claim_ref=ULID_B,
                    from_status=ReviewStatus.draft, to_status=ReviewStatus.draft)


def test_blind_audit_context_recorded():
    e = ReviewEvent(event_id=ULID_A, at=NOW, actor="李宗鴻", claim_ref=ULID_B,
                    from_status=ReviewStatus.queued_manual, to_status=ReviewStatus.approved,
                    label_ref=ULID_A, context="blind_audit", duration_ms=4200)
    assert ReviewEvent.model_validate_json(e.model_dump_json()) == e


# ---- Manifest（D5/D8/防線二） ----


def test_manifest_roundtrip_and_negative_sample():
    m = DatasetVersionManifest(
        version_id=ULID_A, version_number=1, created_at=NOW,
        entries=(
            ManifestEntry(media_hash=SHA, label_refs=(ULID_B,), split="train"),
            ManifestEntry(media_hash=SHA2, label_refs=(), split="val"),  # 純背景負樣本
        ),
        provenance=ProvenanceSummary(human=1, machine_assisted=0, imported=1),
    )
    assert DatasetVersionManifest.model_validate_json(m.model_dump_json()) == m


def test_manifest_rejects_duplicate_media():
    with pytest.raises(ValidationError):
        DatasetVersionManifest(
            version_id=ULID_A, version_number=2, created_at=NOW, parent_ref=ULID_B,
            entries=(
                ManifestEntry(media_hash=SHA, label_refs=(), split="train"),
                ManifestEntry(media_hash=SHA, label_refs=(), split="val"),
            ),
            provenance=ProvenanceSummary(human=0, machine_assisted=0, imported=2),
        )


def test_golden_retirement_needs_reason():
    with pytest.raises(ValidationError):
        GoldenSetEntry(entry_id=ULID_A, media_hash=SHA, label_ref=ULID_B,
                       added_by="李宗鴻", added_at=NOW, status="retired")
    ok = GoldenSetEntry(entry_id=ULID_A, media_hash=SHA, label_ref=ULID_B,
                        added_by="李宗鴻", added_at=NOW, status="retired",
                        retired_reason="場景已淘汰：產線 A 停用")
    assert ok.status == "retired"


def test_timestamps_must_be_tz_aware():
    with pytest.raises(ValidationError):
        make_decision(at=datetime(2026, 7, 7, 12, 0, 0))
