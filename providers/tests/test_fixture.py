from datetime import UTC, datetime

from visionforge_core.calibration import CalibrationObservation, apply_calibration, calibrate
from visionforge_core.contracts import BBox, Concept, ProviderCapability
from visionforge_core.providers import InferenceRequest, VisionProvider
from visionforge_providers import FixtureProvider


def test_fixture_satisfies_provider_protocol():
    provider = FixtureProvider()

    assert isinstance(provider, VisionProvider)


def test_fixture_capability_is_fixed_and_valid():
    capability = FixtureProvider().capability

    assert isinstance(capability, ProviderCapability)
    assert capability.provider_id == "fixture"
    assert capability.version == "0.1.0"
    assert capability.role == "teacher"
    assert capability.locality == "local"
    assert capability.tasks == ("detect",)
    assert capability.promptable_by == ("text",)
    assert capability.reproducible is True
    assert capability.trainable is False
    assert capability.cost_profile == "free_local"


def test_fixture_inference_is_deterministic():
    provider = FixtureProvider()
    request = InferenceRequest(concepts=(Concept(raw_text="bolt"), Concept(raw_text="rust"),))

    first = provider.infer(b"not-an-image", request)
    second = provider.infer(b"not-an-image", request)

    assert first == second
    assert first.provider_id == "fixture"


def test_fixture_returns_one_valid_presence_claim_per_concept():
    provider = FixtureProvider()
    concepts = (Concept(raw_text="bolt"), Concept(raw_text="rust"), Concept(raw_text="crack"))

    result = provider.infer(b"", InferenceRequest(concepts=concepts))

    assert len(result.claims) == len(concepts)
    for claim, concept in zip(result.claims, concepts, strict=True):
        assert claim.assertion == "presence"
        assert claim.concept.raw_text == concept.raw_text
        assert isinstance(claim.geometry, BBox)
        assert 0.0 <= claim.geometry.x1 < claim.geometry.x2 <= 1.0
        assert 0.0 <= claim.geometry.y1 < claim.geometry.y2 <= 1.0
        assert 0.0 < claim.confidence.raw < 1.0


def test_fixture_empty_concepts_return_no_claims_for_any_bytes():
    provider = FixtureProvider()

    assert provider.infer(b"", InferenceRequest()).claims == ()
    assert provider.infer(b"\x00\xffarbitrary", InferenceRequest()).claims == ()


def test_fixture_claims_can_flow_through_calibration():
    provider = FixtureProvider()
    concept = Concept(raw_text="bolt")
    result = provider.infer(b"fake", InferenceRequest(concepts=(concept,)))
    confidence = result.claims[0].confidence
    observations = [
        CalibrationObservation(concept_key=concept.raw_text, raw=confidence.raw, correct=True),
        CalibrationObservation(concept_key=concept.raw_text, raw=0.1, correct=False),
    ]

    snapshot = calibrate(
        observations,
        calibration_id="00000000000000000000000001",
        created_at=datetime(2026, 7, 8, tzinfo=UTC),
        golden_manifest_ref="00000000000000000000000002",
        n_min=1,
        n_high=2,
    )
    calibrated = apply_calibration(confidence, snapshot, concept.raw_text)

    assert 0.0 <= calibrated.raw <= 1.0
    assert calibrated.reliability.value in {"low", "high"}
