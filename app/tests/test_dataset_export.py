from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from visionforge_app.api import create_app
from visionforge_app.export import export_dataset
from visionforge_core.storage import create_project

NOW = datetime(2026, 7, 9, 11, 0, 0, tzinfo=timezone.utc)
VERSION_A = "0000000000000000000000000A"
VERSION_B = "0000000000000000000000000B"


@pytest.fixture()
def project(tmp_path: Path):
    proj = create_project(tmp_path / "project", "export-test", "8" * 26)
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


def _reviewed_media(client: TestClient) -> str:
    imported = client.post(
        "/import",
        files={"file": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert imported.status_code == 200
    media_hash = imported.json()["media_hash"]
    processed = client.post(
        "/process",
        json={
            "media_hash": media_hash,
            "concepts": [{"raw_text": "bolt"}, {"raw_text": "crack"}],
        },
    )
    assert processed.status_code == 200
    pending = client.get("/review/pending")
    assert pending.status_code == 200
    for item in pending.json():
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
    return media_hash


def test_yolo_export_writes_images_labels_yaml_and_manifest(
    client: TestClient,
    project,
) -> None:
    media_hash = _reviewed_media(client)

    outcome = export_dataset(project, "yolo", version_id=VERSION_A, created_at=NOW)

    manifest = project.manifests.get(VERSION_A)
    assert outcome.version_id == VERSION_A
    assert outcome.image_count == 1
    assert outcome.label_count == 2
    assert set(outcome.class_names) == {"bolt", "crack"}
    assert manifest.version_number == 1
    entry = manifest.entries[0]
    image_path = outcome.out_dir / "images" / entry.split / f"{media_hash}.jpg"
    label_path = outcome.out_dir / "labels" / entry.split / f"{media_hash}.txt"
    assert image_path.read_bytes() == project.blobs.find(media_hash).read_bytes()

    lines = label_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        class_id, *coords = line.split()
        assert int(class_id) in (0, 1)
        assert all(0 <= float(value) <= 1 for value in coords)

    data_yaml = (outcome.out_dir / "data.yaml").read_text(encoding="utf-8")
    assert "nc: 2" in data_yaml
    for index, name in enumerate(outcome.class_names):
        assert f'{index}: "{name}"' in data_yaml


def test_coco_export_writes_annotations_and_copies_images(
    client: TestClient,
    project,
) -> None:
    media_hash = _reviewed_media(client)

    outcome = export_dataset(project, "coco", version_id=VERSION_A, created_at=NOW)

    payload = json.loads((outcome.out_dir / "annotations.json").read_text(encoding="utf-8"))
    assert outcome.image_count == 1
    assert outcome.label_count == 2
    assert [category["name"] for category in payload["categories"]] == list(outcome.class_names)
    assert set(outcome.class_names) == {"bolt", "crack"}
    assert len(payload["images"]) == 1
    assert len(payload["annotations"]) == 2
    assert (outcome.out_dir / "images" / f"{media_hash}.jpg").read_bytes() == project.blobs.find(
        media_hash
    ).read_bytes()
    for annotation in payload["annotations"]:
        x, y, width, height = annotation["bbox"]
        assert x >= 0 and y >= 0
        assert width > 0 and height > 0
        assert annotation["area"] == width * height


def test_class_mapping_is_stable_across_versions(client: TestClient, project) -> None:
    _reviewed_media(client)

    first = export_dataset(project, "yolo", version_id=VERSION_A, created_at=NOW)
    second = export_dataset(project, "yolo", version_id=VERSION_B, created_at=NOW)

    assert first.class_names == second.class_names
    assert set(first.class_names) == {"bolt", "crack"}
    assert project.manifests.get(VERSION_B).parent_ref == VERSION_A
    assert (first.out_dir / "data.yaml").read_text(encoding="utf-8").splitlines()[4:] == (
        second.out_dir / "data.yaml"
    ).read_text(encoding="utf-8").splitlines()[4:]


def test_export_endpoint_returns_stringified_outcome(client: TestClient, project) -> None:
    _reviewed_media(client)

    response = client.post("/export", json={"fmt": "coco"})

    assert response.status_code == 200
    body = response.json()
    assert body["fmt"] == "coco"
    assert body["image_count"] == 1
    assert body["label_count"] == 2
    assert set(body["class_names"]) == {"bolt", "crack"}
    assert Path(body["out_dir"]).is_dir()
    assert project.manifests.get(body["version_id"]).version_id == body["version_id"]


def test_export_endpoint_rejects_empty_dataset(client: TestClient, project) -> None:
    response = client.post("/export", json={"fmt": "yolo"})

    assert response.status_code == 409
    assert "沒有已審 Label" in response.json()["detail"]["error"]
    assert not (project.root / "exports").exists()
