from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from visionforge_app.importer import import_media
from visionforge_app.processing import UnknownMediaError, process_media
from visionforge_core.calibration import CalibrationObservation, calibrate
from visionforge_core.contracts import (
    BBox,
    Claim,
    Concept,
    Confidence,
    MediaSource,
    ProviderCapability,
    Reliability,
)
from visionforge_core.providers import InferenceRequest, InferenceResult
from visionforge_core.storage import create_project

NOW = datetime(2026, 7, 9, 9, 30, 0, tzinfo=timezone.utc)


def _ulids() -> list[str]:
    return [
        "0000000000000000000000000A",
        "0000000000000000000000000B",
        "0000000000000000000000000C",
        "0000000000000000000000000D",
    ]


def _id_factory():
    ids = iter(_ulids())
    return lambda: next(ids)


def _jpeg_bytes(size: tuple[int, int] = (16, 10)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, (32, 96, 160)).save(output, format="JPEG")
    return output.getvalue()


def _project(tmp_path: Path, name: str):
    return create_project(tmp_path / name, name, "00000000000000000000000009")


def _import_sample(project) -> str:
    outcome = import_media(
        project,
        _jpeg_bytes(),
        MediaSource(kind="file", detail="sample.jpg"),
    )
    return outcome.media_hash


def test_process_media_records_run_decision_cost_and_outcome(tmp_path: Path) -> None:
    project = _project(tmp_path, "process")
    try:
        media_hash = _import_sample(project)

        outcome = process_media(
            project,
            media_hash,
            [Concept(raw_text="bolt")],
            now=NOW,
            id_factory=_id_factory(),
        )

        run = outcome.run
        assert project.runs.get(run.run_id).run_id == run.run_id
        assert len(run.claims) == 1
        assert run.claims[0].concept.raw_text == "bolt"
        assert run.claims[0].confidence.reliability is Reliability.none
        assert run.claims[0].confidence.calibrated is None
        assert project.runs.get_claim(run.claims[0].claim_id).concept.raw_text == "bolt"

        decision = project.decisions.get(run.decision_ref)
        assert decision.kind == "invoke_provider"
        assert decision.choice.target == "fixture@0.1.0"
        assert len(project.costs.iter_by_subject("run", run.run_id)) == 1

        outcomes = project.decisions.iter_outcomes(run.decision_ref)
        assert len(outcomes) == 1
        assert outcomes[0].status == "success"
    finally:
        project.close()


class StaticBoltProvider:
    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="static-fixture",
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
                    claim_id="0000000000000000000000000E",
                    geometry=BBox(x1=0.1, y1=0.1, x2=0.4, y2=0.4),
                    concept=Concept(raw_text="bolt"),
                    confidence=Confidence(raw=0.9),
                ),
            ),
            provider_id="static-fixture",
        )


def test_process_media_persists_latest_calibration(tmp_path: Path) -> None:
    project = _project(tmp_path, "calibrated")
    try:
        snapshot = calibrate(
            [CalibrationObservation(concept_key="bolt", raw=0.9, correct=True) for _ in range(30)],
            calibration_id="0000000000000000000000000F",
            created_at=NOW,
            golden_manifest_ref="0000000000000000000000000G",
        )
        project.calibrations.append(snapshot)
        media_hash = _import_sample(project)

        outcome = process_media(
            project,
            media_hash,
            [Concept(raw_text="bolt")],
            provider=StaticBoltProvider(),
            now=NOW,
            id_factory=_id_factory(),
        )

        stored = project.runs.get_claim(outcome.run.claims[0].claim_id)
        assert stored.confidence.reliability is Reliability.low
        assert stored.confidence.calibrated is not None
        assert stored.confidence.calibration_ref == snapshot.calibration_id
    finally:
        project.close()


def test_process_media_is_deterministic_with_injected_clock_and_ids(tmp_path: Path) -> None:
    first = _project(tmp_path, "first")
    second = _project(tmp_path, "second")
    try:
        media_a = _import_sample(first)
        media_b = _import_sample(second)

        run_a = process_media(
            first,
            media_a,
            [Concept(raw_text="bolt")],
            now=NOW,
            id_factory=_id_factory(),
        ).run
        run_b = process_media(
            second,
            media_b,
            [Concept(raw_text="bolt")],
            now=NOW,
            id_factory=_id_factory(),
        ).run

        assert run_a.model_dump() == run_b.model_dump()
    finally:
        first.close()
        second.close()


def test_process_media_unknown_media_is_explicit(tmp_path: Path) -> None:
    project = _project(tmp_path, "missing")
    try:
        with pytest.raises(UnknownMediaError):
            process_media(
                project,
                "f" * 64,
                [Concept(raw_text="bolt")],
                now=NOW,
                id_factory=_id_factory(),
            )
    finally:
        project.close()
