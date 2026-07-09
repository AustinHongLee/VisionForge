from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from visionforge_app.importer import import_media
from visionforge_app.processing import UnknownMediaError, process_media
from visionforge_core.contracts import Concept, MediaSource
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
