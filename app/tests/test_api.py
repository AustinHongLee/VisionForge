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


def test_import_bad_bytes_returns_422(client: TestClient) -> None:
    response = client.post(
        "/import",
        files={"file": ("bad.jpg", b"not an image", "image/jpeg")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["error"]
