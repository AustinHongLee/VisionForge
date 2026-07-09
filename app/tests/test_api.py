from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from visionforge_app.api import create_app
from visionforge_core.contracts import Claim
from visionforge_core.storage import create_project


@pytest.fixture()
def project(tmp_path: Path):
    proj = create_project(tmp_path / "project", "api-test", "9" * 26)
    try:
        yield proj
    finally:
        proj.close()


@pytest.fixture()
def client(project) -> TestClient:
    return TestClient(create_app(project))


def _jpeg_bytes(size: tuple[int, int] = (16, 10)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, (32, 96, 160)).save(output, format="JPEG")
    return output.getvalue()


def _import_image(client: TestClient, data: bytes | None = None) -> dict:
    image = data if data is not None else _jpeg_bytes()
    response = client.post(
        "/import",
        files={"file": ("sample.jpg", image, "image/jpeg")},
    )
    assert response.status_code == 200
    return response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_local_renderer_origin(client: TestClient) -> None:
    response = client.options(
        "/infer",
        headers={
            "Access-Control-Request-Headers": "content-type",
            "Access-Control-Request-Method": "POST",
            "Origin": "http://localhost:5173",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_cors_allows_file_origin_for_packaged_renderer(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "null"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "null"


def test_cors_rejects_non_local_origins(client: TestClient) -> None:
    response = client.options(
        "/infer",
        headers={
            "Access-Control-Request-Method": "POST",
            "Origin": "https://example.com",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_import_and_media_listing(client: TestClient) -> None:
    data = _jpeg_bytes()

    imported = _import_image(client, data)
    media = client.get("/media").json()

    assert imported["media_hash"] == hashlib.sha256(data).hexdigest()
    assert imported["deduplicated"] is False
    assert imported["record"]["format"] == "jpeg"
    assert media["total"] == 1
    assert media["items"][0]["media_hash"] == imported["media_hash"]


def test_reimport_is_deduplicated_and_total_does_not_increase(client: TestClient) -> None:
    data = _jpeg_bytes()

    first = _import_image(client, data)
    second = _import_image(client, data)
    media = client.get("/media").json()

    assert second["media_hash"] == first["media_hash"]
    assert second["deduplicated"] is True
    assert media["total"] == 1


def test_media_pagination(client: TestClient) -> None:
    _import_image(client, _jpeg_bytes((16, 10)))
    _import_image(client, _jpeg_bytes((17, 10)))

    response = client.get("/media", params={"limit": 1, "offset": 0})

    assert response.status_code == 200
    page = response.json()
    assert len(page["items"]) == 1
    assert page["total"] == 2
    assert page["limit"] == 1
    assert page["offset"] == 0
    assert page["has_more"] is True


def test_thumbnail_endpoint(client: TestClient) -> None:
    imported = _import_image(client)

    found = client.get(f"/media/{imported['media_hash']}/thumbnail")
    missing = client.get(f"/media/{'f' * 64}/thumbnail")

    assert found.status_code == 200
    assert found.headers["content-type"].startswith("image/jpeg")
    assert found.content.startswith(b"\xff\xd8")
    assert missing.status_code == 404


def test_infer_uses_fixture_provider_and_returns_valid_claims(client: TestClient) -> None:
    imported = _import_image(client)

    response = client.post(
        "/infer",
        json={"media_hash": imported["media_hash"], "concepts": [{"raw_text": "bolt"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider_id"] == "fixture"
    assert len(body["claims"]) == 1
    claim = Claim.model_validate(body["claims"][0])
    assert claim.concept.raw_text == "bolt"


def test_infer_unknown_media_returns_404(client: TestClient) -> None:
    response = client.post(
        "/infer",
        json={"media_hash": "f" * 64, "concepts": [{"raw_text": "bolt"}]},
    )

    assert response.status_code == 404


def test_process_endpoint_records_run_summary(client: TestClient, project) -> None:
    imported = _import_image(client)

    response = client.post(
        "/process",
        json={"media_hash": imported["media_hash"], "concepts": [{"raw_text": "bolt"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["claim_count"] == 1
    run = project.runs.get(body["run_id"])
    assert run.run_id == body["run_id"]
    assert run.claims[0].confidence.reliability.value == "none"
    assert run.claims[0].confidence.calibrated is None
    assert project.decisions.get(body["decision_ref"]).kind == "invoke_provider"
    assert len(project.costs.iter_by_subject("run", body["run_id"])) == 1


def test_process_unknown_media_returns_404(client: TestClient) -> None:
    response = client.post(
        "/process",
        json={"media_hash": "f" * 64, "concepts": [{"raw_text": "bolt"}]},
    )

    assert response.status_code == 404


def _process_image(client: TestClient, concepts: list[str] | None = None) -> dict:
    imported = _import_image(client)
    response = client.post(
        "/process",
        json={
            "media_hash": imported["media_hash"],
            "concepts": [{"raw_text": text} for text in (concepts or ["bolt"])],
        },
    )
    assert response.status_code == 200
    return response.json()


def test_review_pending_lists_processed_claims(client: TestClient) -> None:
    _process_image(client)

    response = client.get("/review/pending")

    assert response.status_code == 200
    pending = response.json()
    assert len(pending) == 1
    assert pending[0]["claim"]["concept"]["raw_text"] == "bolt"
    assert pending[0]["run_ref"]
    assert pending[0]["media_hash"]


def test_review_approve_returns_label_and_removes_pending_claim(
    client: TestClient,
) -> None:
    _process_image(client)
    pending = client.get("/review/pending").json()[0]

    response = client.post(
        "/review/approve",
        json={
            "claim_id": pending["claim"]["claim_id"],
            "run_ref": pending["run_ref"],
            "media_hash": pending["media_hash"],
            "reviewer": "alice",
        },
    )

    assert response.status_code == 200
    label = response.json()
    assert label["claim_ref"] == pending["claim"]["claim_id"]
    assert label["source_status"] == "approved"
    assert label["final_concept"]["taxonomy_node_id"]
    assert label["final_concept"]["mapping_provenance"]["kind"] == "human"
    assert client.get("/review/pending").json() == []


def test_review_approve_with_geometry_edit_marks_edited(client: TestClient) -> None:
    _process_image(client)
    pending = client.get("/review/pending").json()[0]

    response = client.post(
        "/review/approve",
        json={
            "claim_id": pending["claim"]["claim_id"],
            "run_ref": pending["run_ref"],
            "media_hash": pending["media_hash"],
            "reviewer": "alice",
            "final_geometry": {"type": "bbox", "x1": 0.2, "y1": 0.2, "x2": 0.9, "y2": 0.9},
        },
    )

    assert response.status_code == 200
    label = response.json()
    assert label["source_status"] == "edited_approved"
    assert label["final_geometry"]["x2"] == 0.9


def test_review_reject_removes_pending_without_label(client: TestClient, project) -> None:
    _process_image(client)
    pending = client.get("/review/pending").json()[0]

    response = client.post(
        "/review/reject",
        json={
            "claim_id": pending["claim"]["claim_id"],
            "run_ref": pending["run_ref"],
            "media_hash": pending["media_hash"],
            "reviewer": "alice",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["to_status"] == "rejected"
    assert body["event_id"]
    assert client.get("/review/pending").json() == []
    assert project.labels.iter_by_media(pending["media_hash"]) == []


def test_golden_endpoint_registers_approved_label(client: TestClient) -> None:
    _process_image(client)
    pending = client.get("/review/pending").json()[0]
    approved = client.post(
        "/review/approve",
        json={
            "claim_id": pending["claim"]["claim_id"],
            "run_ref": pending["run_ref"],
            "media_hash": pending["media_hash"],
            "reviewer": "alice",
        },
    ).json()

    response = client.post("/golden", json={"label_id": approved["label_id"], "added_by": "alice"})

    assert response.status_code == 200
    entry = response.json()
    assert entry["status"] == "active"
    assert entry["label_ref"] == approved["label_id"]
    assert entry["media_hash"] == approved["media_hash"]


def test_recalibrate_without_reviews_returns_204(client: TestClient) -> None:
    response = client.post("/recalibrate")

    assert response.status_code == 204
    assert response.content == b""


def test_recalibrate_updates_infer_confidence(client: TestClient) -> None:
    imported = _import_image(client)
    process = client.post(
        "/process",
        json={
            "media_hash": imported["media_hash"],
            "concepts": [{"raw_text": "bolt"} for _ in range(30)],
        },
    )
    assert process.status_code == 200

    pending = client.get("/review/pending").json()
    assert len(pending) == 30
    for item in pending:
        approved = client.post(
            "/review/approve",
            json={
                "claim_id": item["claim"]["claim_id"],
                "run_ref": item["run_ref"],
                "media_hash": item["media_hash"],
                "reviewer": "alice",
            },
        )
        assert approved.status_code == 200

    recalibrated = client.post("/recalibrate")
    assert recalibrated.status_code == 200
    snapshot = recalibrated.json()

    inferred = client.post(
        "/infer",
        json={"media_hash": imported["media_hash"], "concepts": [{"raw_text": "bolt"}]},
    )

    assert inferred.status_code == 200
    confidence = inferred.json()["claims"][0]["confidence"]
    assert confidence["reliability"] == "low"
    assert confidence["calibrated"] is not None
    assert confidence["calibration_ref"] == snapshot["calibration_id"]


def test_review_and_golden_unknown_ids_return_404(client: TestClient) -> None:
    missing_claim = client.post(
        "/review/approve",
        json={
            "claim_id": "0000000000000000000000000A",
            "run_ref": "0000000000000000000000000B",
            "media_hash": "f" * 64,
            "reviewer": "alice",
        },
    )
    missing_label = client.post(
        "/golden",
        json={"label_id": "0000000000000000000000000C", "added_by": "alice"},
    )

    assert missing_claim.status_code == 404
    assert missing_label.status_code == 404


def test_import_bad_bytes_returns_422(client: TestClient) -> None:
    response = client.post(
        "/import",
        files={"file": ("bad.jpg", b"not an image", "image/jpeg")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["error"]
