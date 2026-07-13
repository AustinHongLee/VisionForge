"""儲存層測試（ADR-0005）：專案生命週期、去重、append-only、交易原子性。"""

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from visionforge_core.contracts import (
    BBox,
    Claim,
    Concept,
    Confidence,
    CostAgent,
    CostEntry,
    CostMeasurement,
    DatasetVersionManifest,
    DecisionChoice,
    DecisionOutcome,
    DecisionRecord,
    GoldenSetEntry,
    InferenceRun,
    InputRef,
    ManifestEntry,
    MediaRecord,
    MediaSource,
    MediaSubject,
    PolicyRef,
    Producer,
    ProvenanceSummary,
    ReviewEvent,
    ReviewStatus,
)
from visionforge_core.storage import (
    ConflictError,
    NotAProjectError,
    NotFoundError,
    ProjectSchemaTooNewError,
    create_project,
    open_project,
)

NOW = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)


def ulid(n: int) -> str:
    return f"{n:026d}"


def sha(n: int) -> str:
    return f"{n:064x}"


@pytest.fixture()
def project(tmp_path):
    proj = create_project(tmp_path / "proj", "測試專案", ulid(1))
    yield proj
    proj.close()


def make_media(n: int = 1) -> MediaRecord:
    return MediaRecord(
        media_hash=sha(n), width_px=1920, height_px=1080, format="jpeg",
        byte_size=12345, imported_at=NOW,
        source=MediaSource(kind="folder", detail="D:/photos"), exif_normalized=True,
    )


def make_claim(n: int) -> Claim:
    return Claim(
        claim_id=ulid(n),
        geometry=BBox(x1=0.1, y1=0.1, x2=0.5, y2=0.5),
        concept=Concept(raw_text="rusty bolt"),
        confidence=Confidence(raw=0.8),
    )


def make_run(n: int = 10, claims: tuple = ()) -> InferenceRun:
    return InferenceRun(
        run_id=ulid(n),
        subject=MediaSubject(media_hash=sha(1), width_px=1920, height_px=1080),
        producer=Producer(provider_id="gdino", provider_version="1.5", params_hash=sha(9)),
        task="detect", created_at=NOW, duration_ms=100,
        cost_ref=ulid(90), decision_ref=ulid(91), claims=claims,
    )


# ---- 專案生命週期 ----


def test_create_and_reopen(tmp_path):
    root = tmp_path / "p1"
    proj = create_project(root, "專案甲", ulid(1))
    proj.close()
    reopened = open_project(root)  # 遷移冪等：重開不得炸
    assert reopened.media.count() == 0
    assert (root / "project.json").is_file()
    assert (root / "media" / "blobs").is_dir()
    reopened.close()


def test_create_rejects_nonempty(tmp_path):
    root = tmp_path / "dirty"
    root.mkdir()
    (root / "x.txt").write_text("x")
    with pytest.raises(NotAProjectError):
        create_project(root, "p", ulid(1))


def test_open_rejects_non_project(tmp_path):
    with pytest.raises(NotAProjectError):
        open_project(tmp_path)


def test_schema_too_new_refused(tmp_path):
    """D9：舊程式打開新專案必須明確拒絕，不得靜默損毀。"""
    root = tmp_path / "p2"
    proj = create_project(root, "未來專案", ulid(1))
    proj.db.execute(
        "INSERT INTO schema_migrations(version, applied_at) VALUES(999, ?)",
        (NOW.isoformat(),),
    )
    proj.close()
    with pytest.raises(ProjectSchemaTooNewError):
        open_project(root)


def test_v3_project_migrates_additively_to_teaching_schema(tmp_path):
    """既有專案重開時只新增 R3 資料表，不要求使用者重建專案。"""
    root = tmp_path / "legacy-v3"
    project = create_project(root, "舊專案", ulid(1))
    project.close()
    conn = sqlite3.connect(root / "project.db")
    for table in (
        "capability_releases",
        "teacher_consents",
        "evaluation_feedback",
        "evaluation_reports",
        "model_artifacts",
        "training_run_events",
        "training_runs",
        "teaching_dataset_versions",
        "claim_teaching_context",
        "annotation_revisions",
        "coverage",
        "media_assignments",
        "concepts",
        "tasks",
    ):
        conn.execute(f"DROP TABLE {table}")
    conn.execute("DELETE FROM schema_migrations WHERE version >= 4")
    conn.commit()
    conn.close()

    reopened = open_project(root)
    try:
        assert reopened.tasks.list() == []
        assert reopened.db.query_one(
            "SELECT 1 FROM schema_migrations WHERE version = 8"
        ) is not None
    finally:
        reopened.close()


# ---- Blob 庫 ----


def test_blob_dedupe_and_atomicity(project):
    data = b"fake-jpeg-bytes"
    h1 = project.blobs.put(data, "jpeg")
    h2 = project.blobs.put(data, "jpeg")  # 重複寫入＝no-op
    assert h1 == h2
    path = project.blobs.find(h1)
    assert path is not None and path.read_bytes() == data
    assert not list(path.parent.glob("*.tmp"))  # 沒有半成品殘留
    with pytest.raises(ValueError):
        project.blobs.put(data, "gif")  # 封閉格式集合


# ---- Media ----


def test_media_add_get_conflict(project):
    rec = make_media(1)
    project.media.add(rec)
    assert project.media.get(sha(1)) == rec
    assert project.media.exists(sha(1)) and not project.media.exists(sha(2))
    assert project.media.count() == 1
    with pytest.raises(ConflictError):
        project.media.add(rec)
    with pytest.raises(NotFoundError):
        project.media.get(sha(2))


# ---- Run 與 Claims ----


def test_run_append_and_claim_queries(project):
    run = make_run(claims=(make_claim(11), make_claim(12)))
    project.runs.append(run)
    assert project.runs.get(ulid(10)) == run
    assert project.runs.get_claim(ulid(11)) == run.claims[0]
    assert len(project.runs.iter_claims_by_media(sha(1))) == 2
    with pytest.raises(ConflictError):
        project.runs.append(run)


def test_run_append_is_atomic(project):
    """第二個 claim 撞 ID → 整筆 run 必須不存在（整批成功或整批不存在）。"""
    bad = make_run(n=20, claims=(make_claim(21), make_claim(21)))
    with pytest.raises(ConflictError):
        project.runs.append(bad)
    with pytest.raises(NotFoundError):
        project.runs.get(ulid(20))
    with pytest.raises(NotFoundError):
        project.runs.get_claim(ulid(21))


# ---- 帳本 ----


def test_decision_and_outcomes(project):
    d = DecisionRecord(
        decision_id=ulid(30), at=NOW, kind="route_claim",
        policy=PolicyRef(policy_hash=sha(5), policy_label="rules-v1"),
        inputs=(InputRef(kind="claim", id=ulid(11)),),
        choice=DecisionChoice(target="queued_manual", reason_code="uncalibrated"),
    )
    project.decisions.append(d)
    assert project.decisions.get(ulid(30)) == d
    o = DecisionOutcome(outcome_id=ulid(31), decision_ref=ulid(30), at=NOW, status="success")
    project.decisions.append_outcome(o)
    assert project.decisions.iter_outcomes(ulid(30)) == [o]


def test_cost_by_subject(project):
    est = CostEntry(
        cost_id=ulid(40), at=NOW, phase="estimate",
        subject=InputRef(kind="run", id=ulid(10)),
        agent=CostAgent(kind="provider", id="gdino", version="1.5"),
        measurements=(CostMeasurement(unit="seconds", amount=Decimal("1.5")),),
    )
    act = est.model_copy(update={"cost_id": ulid(41), "phase": "actual",
                                 "estimate_ref": ulid(40)})
    project.costs.append(est)
    project.costs.append(act)
    got = project.costs.iter_by_subject("run", ulid(10))
    assert [c.phase for c in got] == ["estimate", "actual"]


def test_review_events_ordered(project):
    e1 = ReviewEvent(event_id=ulid(50), at=NOW, actor="李宗鴻", claim_ref=ulid(11),
                     from_status=ReviewStatus.draft, to_status=ReviewStatus.queued_manual)
    e2 = ReviewEvent(event_id=ulid(51), at=NOW, actor="李宗鴻", claim_ref=ulid(11),
                     from_status=ReviewStatus.queued_manual,
                     to_status=ReviewStatus.rejected)
    project.review_events.append(e2)
    project.review_events.append(e1)
    got = project.review_events.iter_by_claim(ulid(11))
    assert [e.event_id for e in got] == [ulid(50), ulid(51)]  # at 同 → 依 event_id


# ---- Manifest 與黃金集 ----


def test_manifest_roundtrip_latest_and_unique_number(project):
    m1 = DatasetVersionManifest(
        version_id=ulid(60), version_number=1, created_at=NOW,
        entries=(
            ManifestEntry(media_hash=sha(1), label_refs=(ulid(70),), split="train"),
            ManifestEntry(media_hash=sha(2), label_refs=(), split="val"),
        ),
        provenance=ProvenanceSummary(human=1, machine_assisted=0, imported=1),
    )
    project.manifests.append(m1)
    assert project.manifests.get(ulid(60)) == m1  # 正規化後重組，全量重驗
    m2 = m1.model_copy(update={"version_id": ulid(61), "version_number": 2,
                               "parent_ref": ulid(60)})
    project.manifests.append(m2)
    latest = project.manifests.latest()
    assert latest is not None and latest.version_number == 2
    dup = m1.model_copy(update={"version_id": ulid(62)})  # number=1 重複
    with pytest.raises(ConflictError):
        project.manifests.append(dup)


def test_golden_active_only(project):
    a = GoldenSetEntry(entry_id=ulid(80), media_hash=sha(1), label_ref=ulid(70),
                       added_by="李宗鴻", added_at=NOW)
    r = GoldenSetEntry(entry_id=ulid(81), media_hash=sha(2), label_ref=ulid(71),
                       added_by="李宗鴻", added_at=NOW, status="retired",
                       retired_reason="場景淘汰")
    project.golden.append(a)
    project.golden.append(r)
    assert [e.entry_id for e in project.golden.iter_active()] == [ulid(80)]
