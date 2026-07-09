from __future__ import annotations

import json
import sys
import types

import pytest
from visionforge_core.contracts import BBox, Concept, ProviderCapability
from visionforge_core.providers import InferenceRequest, VisionProvider
from visionforge_providers import OpenAIProviderError, OpenAIVisionProvider, openai_vision


class FakeResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class FakeResponses:
    def __init__(self, output_text: str | None = None, error: Exception | None = None) -> None:
        self.output_text = output_text
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return FakeResponse(self.output_text or '{"boxes":[]}')


class FakeClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def _provider(responses: FakeResponses) -> OpenAIVisionProvider:
    return OpenAIVisionProvider(
        api_key="sk-test-secret",
        model="gpt-5-mini",
        client=FakeClient(responses),
    )


def test_openai_provider_satisfies_protocol_and_capability() -> None:
    provider = _provider(FakeResponses())

    assert isinstance(provider, VisionProvider)
    capability = provider.capability
    assert isinstance(capability, ProviderCapability)
    assert capability.provider_id == "openai"
    assert capability.version == "gpt-5-mini"
    assert capability.role == "teacher"
    assert capability.locality == "cloud"
    assert capability.tasks == ("detect",)
    assert capability.promptable_by == ("text",)
    assert capability.reproducible is False
    assert capability.trainable is False
    assert capability.cost_profile == "api_metered"


def test_openai_provider_maps_structured_output_to_claims() -> None:
    responses = FakeResponses(
        json.dumps(
            {
                "boxes": [
                    {"concept": "bolt", "box": [0.1, 0.2, 0.4, 0.6], "confidence": 0.75},
                    {"concept": "crack", "box": [0.5, 0.1, 0.9, 0.3], "confidence": 0.33},
                ]
            }
        )
    )
    provider = _provider(responses)

    result = provider.infer(
        b"\xff\xd8fake-jpeg",
        InferenceRequest(concepts=(Concept(raw_text="bolt"), Concept(raw_text="crack"))),
    )

    assert result.provider_id == "openai"
    assert len(result.claims) == 2
    assert result.claims[0].concept.raw_text == "bolt"
    assert isinstance(result.claims[0].geometry, BBox)
    assert result.claims[0].geometry.x1 == 0.1
    assert result.claims[0].geometry.y2 == 0.6
    assert result.claims[0].confidence.raw == 0.75
    call = responses.calls[0]
    assert call["model"] == "gpt-5-mini"
    assert call["input"][0]["content"][1]["type"] == "input_image"
    assert call["input"][0]["content"][1]["image_url"].startswith("data:image/jpeg;base64,")
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True


def test_openai_provider_clamps_out_of_bounds_and_drops_degenerate_boxes() -> None:
    provider = _provider(
        FakeResponses(
            json.dumps(
                {
                    "boxes": [
                        {"concept": "bolt", "box": [-0.1, 0.2, 1.2, 0.6], "confidence": 1.4},
                        {"concept": "bolt", "box": [0.4, 0.4, 0.4, 0.9], "confidence": 0.5},
                        {"concept": "other", "box": [0.1, 0.1, 0.2, 0.2], "confidence": 0.9},
                    ]
                }
            )
        )
    )

    result = provider.infer(b"png", InferenceRequest(concepts=(Concept(raw_text="bolt"),)))

    assert len(result.claims) == 1
    bbox = result.claims[0].geometry
    assert isinstance(bbox, BBox)
    assert bbox.x1 == 0.0
    assert bbox.x2 == 1.0
    assert result.claims[0].confidence.raw == 1.0


def test_openai_provider_invalid_json_returns_empty_claims() -> None:
    provider = _provider(FakeResponses("not json"))

    result = provider.infer(b"", InferenceRequest(concepts=(Concept(raw_text="bolt"),)))

    assert result.claims == ()


def test_openai_provider_api_error_does_not_leak_key() -> None:
    provider = _provider(FakeResponses(error=RuntimeError("bad key sk-test-secret")))

    with pytest.raises(OpenAIProviderError) as caught:
        provider.infer(b"", InferenceRequest(concepts=(Concept(raw_text="bolt"),)))

    assert "sk-test-secret" not in str(caught.value)
    assert "[redacted]" in str(caught.value)


def test_openai_provider_empty_concepts_skips_client_call() -> None:
    responses = FakeResponses()
    provider = _provider(responses)

    result = provider.infer(b"", InferenceRequest())

    assert result.claims == ()
    assert responses.calls == []


def test_default_client_pins_official_openai_base_url(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeOpenAI:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setitem(
        sys.modules,
        "openai",
        types.SimpleNamespace(OpenAI=FakeOpenAI),
    )

    openai_vision._default_client("sk-test-secret", openai_vision._OPENAI_BASE_URL)

    assert captured["api_key"] == "sk-test-secret"
    assert captured["base_url"] == "https://api.openai.com/v1"
