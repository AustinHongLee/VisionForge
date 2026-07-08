"""Vision Provider 契約與 provisional 介面測試（ADR-0008）。"""

import pytest
from pydantic import ValidationError
from visionforge_core.contracts import (
    BBox,
    Claim,
    Concept,
    Confidence,
    ProviderCapability,
)
from visionforge_core.providers import InferenceRequest, InferenceResult, VisionProvider


def make_capability(**kw) -> ProviderCapability:
    base = dict(
        provider_id="gdino", version="1.5", role="teacher", locality="local",
        tasks=("detect",), promptable_by=("text",), reproducible=True,
        trainable=False, cost_profile="free_local",
    )
    base.update(kw)
    return ProviderCapability(**base)


def test_capability_valid():
    cap = make_capability(tasks=("detect", "segment"), promptable_by=("text", "box"))
    assert cap.role == "teacher"
    assert cap.schema_version == "1.0"


def test_capability_rejects_empty_tasks():
    with pytest.raises(ValidationError):
        make_capability(tasks=())


def test_capability_rejects_duplicate_tasks():
    with pytest.raises(ValidationError):
        make_capability(tasks=("detect", "detect"))


def test_capability_rejects_unknown_task():
    with pytest.raises(ValidationError):
        make_capability(tasks=("teleport",))


def test_capability_rejects_bad_provider_id():
    with pytest.raises(ValidationError):
        make_capability(provider_id="Bad ID!")  # 非 slug


# ---- provisional 介面：可被真實類別實作，runtime_checkable ----

class _FixtureProvider:
    def __init__(self) -> None:
        self._cap = make_capability(provider_id="fixture", reproducible=True)

    @property
    def capability(self) -> ProviderCapability:
        return self._cap

    def infer(self, media_bytes: bytes, request: InferenceRequest) -> InferenceResult:
        claim = Claim(
            claim_id="0" * 26,
            geometry=BBox(x1=0.1, y1=0.1, x2=0.5, y2=0.5),
            concept=request.concepts[0] if request.concepts else Concept(raw_text="object"),
            confidence=Confidence(raw=0.8),
        )
        return InferenceResult(claims=(claim,), provider_id=self._cap.provider_id)


def test_fixture_satisfies_protocol():
    prov = _FixtureProvider()
    assert isinstance(prov, VisionProvider)  # runtime_checkable
    result = prov.infer(b"fake", InferenceRequest(concepts=(Concept(raw_text="bolt"),)))
    assert len(result.claims) == 1
    assert result.claims[0].concept.raw_text == "bolt"
    assert result.provider_id == "fixture"
    assert result.diagnostics == {}
