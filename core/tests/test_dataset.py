"""Dataset 版本快照測試（ADR-0010 收尾，D5）：由已審 Label 建版本清單。"""

from datetime import datetime, timezone

import pytest
from visionforge_core.contracts import BBox, Claim, Concept, Confidence, MediaSubject, Producer
from visionforge_core.dataset import build_version
from visionforge_core.orchestrator import record_inference_run
from visionforge_core.review import approve, list_pending
from visionforge_core.storage import create_project

NOW = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


def sha(n: int) -> str:
    return f"{n:064x}"


def ulid(n: int) -> str:
    return f"{n:026d}"


def claim(n: int, text: str) -> Claim:
    return Claim(
        claim_id=ulid(n),
        geometry=BBox(x1=0.1, y1=0.1, x2=0.4, y2=0.4),
        concept=Concept(raw_text=text),
        confidence=Confidence(raw=0.8),
    )


def seed_two_labels(tmp_path):
    proj = create_project(tmp_path / "p", "q", ulid(1))
    record_inference_run(
        proj,
        subject=MediaSubject(media_hash=sha(1), width_px=800, height_px=600),
        producer=Producer(provider_id="fixture", provider_version="0.1.0", params_hash=sha(9)),
        task="detect",
        claims=(claim(100, "bolt"), claim(101, "crack")),
        duration_ms=10,
        run_id=ulid(10), decision_id=ulid(20), cost_id=ulid(30), outcome_id=ulid(40),
        now=NOW,
    )
    pend = {p.claim.claim_id: p for p in list_pending(proj)}
    approve(proj, pend[ulid(100)], reviewer="a", reviewed_at=NOW,
            node_id=ulid(200), label_id=ulid(300), event_id=ulid(400))
    approve(proj, pend[ulid(101)], reviewer="a", reviewed_at=NOW,
            node_id=ulid(201), label_id=ulid(301), event_id=ulid(401))
    return proj


def test_build_version_groups_labels_by_media(tmp_path):
    proj = seed_two_labels(tmp_path)
    try:
        m = build_version(proj, version_id=ulid(500), created_at=NOW)
        assert m.version_number == 1 and m.parent_ref is None
        assert len(m.entries) == 1  # 兩個 Label 同一 media → 一個 entry
        assert set(m.entries[0].label_refs) == {ulid(300), ulid(301)}
        assert m.entries[0].split in ("train", "val")
        assert m.provenance.human == 2
        # 存得回、重組驗證通過
        assert proj.manifests.get(ulid(500)).version_number == 1
    finally:
        proj.close()


def test_second_version_links_parent(tmp_path):
    proj = seed_two_labels(tmp_path)
    try:
        build_version(proj, version_id=ulid(500), created_at=NOW)
        m2 = build_version(proj, version_id=ulid(501), created_at=NOW)
        assert m2.version_number == 2 and m2.parent_ref == ulid(500)
    finally:
        proj.close()


def test_build_version_rejects_empty(tmp_path):
    proj = create_project(tmp_path / "empty", "q", ulid(1))
    try:
        with pytest.raises(ValueError):
            build_version(proj, version_id=ulid(500), created_at=NOW)
    finally:
        proj.close()
