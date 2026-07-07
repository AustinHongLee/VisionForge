"""Claim Schema v1.0 契約測試——這些測試就是規格（分工協議：測試是兩個 agent 之間唯一的語言）。"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from visionforge_core.contracts import (
    Assertion,
    BBox,
    Claim,
    Concept,
    ConceptMappingProvenance,
    Confidence,
    InferenceRun,
    Label,
    MediaSubject,
    Producer,
    Reliability,
    Review,
    ReviewStatus,
    UnknownGeometry,
    WholeImage,
)

ULID_A = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
ULID_B = "01BX5ZZKBKACTAV9WEVGEMMVRZ"
SHA = "ab" * 32
NOW = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)


def make_claim(**overrides):
    base = dict(
        claim_id=ULID_A,
        geometry=BBox(x1=0.1, y1=0.1, x2=0.5, y2=0.5),
        concept=Concept(raw_text="rusty bolt"),
        confidence=Confidence(raw=0.87),
    )
    base.update(overrides)
    return Claim(**base)


def make_run(**overrides):
    base = dict(
        run_id=ULID_A,
        subject=MediaSubject(media_hash=SHA, width_px=1920, height_px=1080),
        producer=Producer(provider_id="grounding-dino", provider_version="1.5.1", params_hash=SHA),
        task="detect",
        created_at=NOW,
        duration_ms=420,
        cost_ref=ULID_B,
        decision_ref=ULID_B,
        claims=(make_claim(),),
    )
    base.update(overrides)
    return InferenceRun(**base)


# ---- 往返一致（D3/F7：帳本可重放的基礎） ----


def test_run_json_roundtrip():
    run = make_run()
    restored = InferenceRun.model_validate_json(run.model_dump_json())
    assert restored == run


# ---- 幾何 ----


def test_bbox_rejects_zero_area():
    with pytest.raises(ValidationError):
        BBox(x1=0.5, y1=0.1, x2=0.5, y2=0.9)


def test_coordinates_must_be_normalized():
    with pytest.raises(ValidationError):
        BBox(x1=0.1, y1=0.1, x2=1.5, y2=0.5)


def test_unknown_geometry_preserved_not_dropped():
    """F1 前向相容：2032 年的幾何型別，2026 年的核心必須保留原文。"""
    claim = make_claim(
        geometry={"type": "hexmesh3d", "vertices": [1, 2, 3], "note": "future"}
    )
    assert isinstance(claim.geometry, UnknownGeometry)
    assert claim.geometry.interpretable is False
    assert claim.geometry.type == "hexmesh3d"
    restored = Claim.model_validate_json(claim.model_dump_json())
    assert restored.geometry.model_dump()["vertices"] == [1, 2, 3]


def test_malformed_known_geometry_must_fail_not_degrade():
    """壞掉的 bbox 不得偽裝成未來型別溜進帳本。"""
    with pytest.raises(ValidationError):
        make_claim(geometry={"type": "bbox", "x1": 1.5, "y1": 0.1, "x2": 2.0, "y2": 0.5})


# ---- 否定陳述（ADR-0003 裁決 #2） ----


def test_absence_requires_whole_image():
    with pytest.raises(ValidationError):
        make_claim(assertion=Assertion.absence)  # 預設 bbox 幾何 → 違規
    ok = make_claim(assertion=Assertion.absence, geometry=WholeImage())
    assert ok.assertion is Assertion.absence


# ---- 信心校準不變量（憲法 §3） ----


def test_calibrated_requires_ref():
    with pytest.raises(ValidationError):
        Confidence(raw=0.9, calibrated=0.8)


def test_reliability_requires_calibrated():
    with pytest.raises(ValidationError):
        Confidence(raw=0.9, reliability=Reliability.high)


# ---- 審核留痕（P4） ----


def test_terminal_review_requires_reviewer():
    with pytest.raises(ValidationError):
        Review(status=ReviewStatus.approved)


# ---- 帳本強制（D3/D4） ----


def test_run_requires_cost_and_decision_refs():
    with pytest.raises(ValidationError):
        make_run(cost_ref=None)
    with pytest.raises(ValidationError):
        make_run(decision_ref=None)


def test_timestamps_must_be_tz_aware():
    with pytest.raises(ValidationError):
        make_run(created_at=datetime(2026, 7, 7, 12, 0, 0))


# ---- provider_extra 硬上限（ADR-0003 裁決 #4） ----


def test_provider_extra_size_cap():
    with pytest.raises(ValidationError):
        make_claim(provider_extra={"blob": "x" * (64 * 1024 + 1)})
    ok = make_claim(provider_extra={"note": "small"})
    assert ok.provider_extra == {"note": "small"}


# ---- Label 不變量（D7） ----


def _mapped_concept():
    return Concept(
        raw_text="rusty bolt",
        taxonomy_node_id=ULID_B,
        mapping_provenance=ConceptMappingProvenance(kind="human", actor="李宗鴻", mapped_at=NOW),
    )


def make_label(**overrides):
    base = dict(
        label_id=ULID_A,
        claim_ref=ULID_A,
        run_ref=ULID_B,
        media_hash=SHA,
        assertion=Assertion.presence,
        final_geometry=BBox(x1=0.1, y1=0.1, x2=0.5, y2=0.5),
        final_concept=_mapped_concept(),
        reviewer="李宗鴻",
        reviewed_at=NOW,
        source_status="approved",
    )
    base.update(overrides)
    return Label(**base)


def test_label_roundtrip():
    label = make_label()
    assert Label.model_validate_json(label.model_dump_json()) == label


def test_label_rejects_unknown_geometry():
    with pytest.raises(ValidationError):
        make_label(final_geometry={"type": "hexmesh3d", "v": 1})


def test_label_requires_taxonomy_mapping():
    with pytest.raises(ValidationError):
        make_label(final_concept=Concept(raw_text="rusty bolt"))


def test_concept_mapping_requires_provenance():
    """映射本身也是有出處的意見（血統無死角）。"""
    with pytest.raises(ValidationError):
        Concept(raw_text="rusty bolt", taxonomy_node_id=ULID_B)


# ---- 邊界拒絕未知欄位（A5） ----


def test_unknown_fields_rejected_at_boundary():
    with pytest.raises(ValidationError):
        Claim.model_validate(
            {
                "claim_id": ULID_A,
                "geometry": {"type": "whole_image"},
                "concept": {"raw_text": "x"},
                "confidence": {"raw": 0.5},
                "totally_new_field": 123,
          
            }
        )
