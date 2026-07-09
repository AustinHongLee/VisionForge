"""審核狀態機測試（ADR-0010 #3，D7）：待審→approve/edit/reject。"""

from datetime import datetime, timezone

from visionforge_core.contracts import BBox, Claim, Concept, Confidence, MediaSubject, Producer
from visionforge_core.orchestrator import record_inference_run
from visionforge_core.review import approve, list_pending, reject
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


def seed(tmp_path):
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
    return proj


def test_pending_lists_unreviewed(tmp_path):
    proj = seed(tmp_path)
    try:
        pending = list_pending(proj)
        assert {p.claim.claim_id for p in pending} == {ulid(100), ulid(101)}
        assert all(p.run_ref == ulid(10) and p.media_hash == sha(1) for p in pending)
    finally:
        proj.close()


def test_approve_creates_mapped_label_and_shrinks_queue(tmp_path):
    proj = seed(tmp_path)
    try:
        item = next(p for p in list_pending(proj) if p.claim.claim_id == ulid(100))
        label = approve(
            proj, item, reviewer="alice", reviewed_at=NOW,
            node_id=ulid(200), label_id=ulid(300), event_id=ulid(400),
        )
        assert label.source_status == "approved"
        assert label.final_concept.taxonomy_node_id == ulid(200)  # 已映射
        assert label.final_concept.mapping_provenance.kind == "human"
        assert proj.labels.get(ulid(300)).claim_ref == ulid(100)
        # ReviewEvent 記錄且回指 label
        events = proj.review_events.iter_by_claim(ulid(100))
        assert len(events) == 1 and events[0].to_status.value == "approved"
        assert events[0].label_ref == ulid(300)
        # 佇列縮小：已審的不再出現
        assert {p.claim.claim_id for p in list_pending(proj)} == {ulid(101)}
    finally:
        proj.close()


def test_edit_approve_sets_edited_and_overrides_geometry(tmp_path):
    proj = seed(tmp_path)
    try:
        item = next(p for p in list_pending(proj) if p.claim.claim_id == ulid(100))
        new_geom = BBox(x1=0.2, y1=0.2, x2=0.9, y2=0.9)
        label = approve(
            proj, item, reviewer="bob", reviewed_at=NOW,
            node_id=ulid(200), label_id=ulid(300), event_id=ulid(400),
            final_geometry=new_geom,
        )
        assert label.source_status == "edited_approved"
        assert label.final_geometry.x2 == 0.9
    finally:
        proj.close()


def test_reject_creates_event_without_label(tmp_path):
    proj = seed(tmp_path)
    try:
        item = next(p for p in list_pending(proj) if p.claim.claim_id == ulid(101))
        event = reject(proj, item, reviewer="alice", reviewed_at=NOW, event_id=ulid(401))
        assert event.to_status.value == "rejected"
        assert event.label_ref is None
        assert proj.labels.iter_by_media(sha(1)) == []  # 否決不產 Label
        assert {p.claim.claim_id for p in list_pending(proj)} == {ulid(100)}
    finally:
        proj.close()
