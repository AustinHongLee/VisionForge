from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from visionforge_app.api import create_app
from visionforge_app.provider_config import (
    ENV_DEVELOPER_FIXTURE,
    ProviderConfigurationError,
    load_provider,
)
from visionforge_core.contracts import BBox, Claim, Concept, Confidence, ProviderCapability
from visionforge_core.providers import InferenceRequest, InferenceResult
from visionforge_core.storage import create_project
from visionforge_providers import FixtureProvider, OpenAIProviderError, OpenAIVisionProvider


@pytest.fixture()
def project(tmp_path: Path):
    proj = create_project(tmp_path / "project", "provider-config-test", "7" * 26)
    try:
        yield proj
    finally:
        proj.close()


def _jpeg_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (16, 10), (32, 96, 160)).save(output, format="JPEG")
    return output.getvalue()


def test_load_provider_missing_config_is_explicit_error(project) -> None:
    with pytest.raises(ProviderConfigurationError, match="未設定 Teacher"):
        load_provider(project)


def test_load_provider_developer_mode_explicitly_enables_fixture(project, monkeypatch) -> None:
    monkeypatch.setenv(ENV_DEVELOPER_FIXTURE, "1")

    provider = load_provider(project)

    assert isinstance(provider, FixtureProvider)


def test_load_provider_explicit_fixture_ignores_key(project) -> None:
    config = project.root / "provider-config.json"
    config.write_text(
        json.dumps({"provider": "fixture", "model": "gpt-5-mini", "openai_api_key": "sk-secret"}),
        encoding="utf-8",
    )

    provider = load_provider(project)

    assert isinstance(provider, FixtureProvider)


def test_load_provider_uses_openai_when_config_has_key(project) -> None:
    config = project.root / "provider-config.json"
    config.write_text(
        json.dumps({"provider": "openai", "model": "gpt-5-mini", "openai_api_key": "sk-secret"}),
        encoding="utf-8",
    )

    provider = load_provider(project, client=object())

    assert isinstance(provider, OpenAIVisionProvider)
    assert provider.capability.version == "gpt-5-mini"


def test_load_provider_invalid_json_is_explicit_error(project) -> None:
    (project.root / "provider-config.json").write_text("{bad json", encoding="utf-8")

    with pytest.raises(ProviderConfigurationError, match="Teacher 設定無效"):
        load_provider(project)


def test_api_missing_provider_returns_503_instead_of_fake_boxes(project) -> None:
    client = TestClient(create_app(project))
    imported = client.post(
        "/import",
        files={"file": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    response = client.post(
        "/infer",
        json={"media_hash": imported.json()["media_hash"], "concepts": [{"raw_text": "bolt"}]},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "provider_not_configured"


class SingleClaimProvider:
    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="loaded-provider",
            version="0.1.0",
            role="teacher",
            locality="local",
            tasks=("detect",),
            promptable_by=("text",),
            reproducible=True,
            trainable=False,
            cost_profile="free_local",
        )

    def infer(self, media_bytes: bytes, request: InferenceRequest) -> InferenceResult:
        del media_bytes, request
        return InferenceResult(
            claims=(
                Claim(
                    claim_id="0000000000000000000000000A",
                    geometry=BBox(x1=0.1, y1=0.2, x2=0.3, y2=0.4),
                    concept=Concept(raw_text="bolt"),
                    confidence=Confidence(raw=0.88),
                ),
            ),
            provider_id="loaded-provider",
        )


class FailingProvider:
    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="failing-provider",
            version="0.1.0",
            role="teacher",
            locality="cloud",
            tasks=("detect",),
            promptable_by=("text",),
            reproducible=False,
            trainable=False,
            cost_profile="paid_remote",
        )

    def infer(self, media_bytes: bytes, request: InferenceRequest) -> InferenceResult:
        del media_bytes, request
        raise OpenAIProviderError("OpenAI provider failed: invalid key [redacted]")


def test_api_uses_loaded_provider_when_no_override(project, monkeypatch) -> None:
    monkeypatch.setattr(
        "visionforge_app.api.app.load_provider",
        lambda current: SingleClaimProvider(),
    )
    client = TestClient(create_app(project))
    imported = client.post(
        "/import",
        files={"file": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert imported.status_code == 200

    response = client.post(
        "/infer",
        json={"media_hash": imported.json()["media_hash"], "concepts": [{"raw_text": "bolt"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider_id"] == "loaded-provider"
    assert body["claims"][0]["confidence"]["raw"] == 0.88


def test_api_provider_error_returns_cors_502(project, monkeypatch) -> None:
    monkeypatch.setattr(
        "visionforge_app.api.app.load_provider",
        lambda current: FailingProvider(),
    )
    client = TestClient(create_app(project))
    imported = client.post(
        "/import",
        files={"file": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert imported.status_code == 200

    response = client.post(
        "/infer",
        json={"media_hash": imported.json()["media_hash"], "concepts": [{"raw_text": "cat"}]},
        headers={"origin": "http://localhost:5173"},
    )

    assert response.status_code == 502
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    body = response.json()
    assert body["detail"]["error"] == "provider_unavailable"
    assert body["detail"]["message"] == "OpenAI provider failed: invalid key [redacted]"
    assert "sk-" not in body["detail"]["message"]
