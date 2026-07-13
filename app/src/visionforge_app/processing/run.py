"""app 側 process_media：呼叫 provider，交由 core orchestrator 入帳（票-0012）。"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from visionforge_core.calibration import apply_latest
from visionforge_core.contracts import Claim, Concept, InferenceRun, MediaSubject, Producer
from visionforge_core.orchestrator import record_inference_run
from visionforge_core.providers import InferenceRequest, VisionProvider
from visionforge_core.storage import Project
from visionforge_core.storage.errors import NotFoundError
from visionforge_providers import FixtureProvider

_CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


class UnknownMediaError(ValueError):
    """處理流程找不到指定媒體或 blob。"""


@dataclass(frozen=True)
class ProcessOutcome:
    run: InferenceRun


def _new_ulid() -> str:
    timestamp_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    value = (timestamp_ms << 80) | secrets.randbits(80)
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD32[value & 0b11111])
        value >>= 5
    return "".join(reversed(chars))


def _params_hash(*, concepts: Sequence[Concept], task: str, provider_id: str, version: str) -> str:
    payload = {
        "concepts": [concept.model_dump(mode="json") for concept in concepts],
        "provider_id": provider_id,
        "task": task,
        "version": version,
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _claim_id_for_run(run_id: str, index: int) -> str:
    """Provider 的 draft ID 不是全域身分；持久化 ID 由服務層以 Run scope 配置。"""
    digest = hashlib.sha256(f"{run_id}\0{index}".encode("ascii")).digest()
    value = int.from_bytes(digest[:16], "big")
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD32[value & 0b11111])
        value >>= 5
    return "".join(reversed(chars))


def apply_latest_to_claims(project: Project, claims: Sequence[Claim]) -> tuple[Claim, ...]:
    """用最新校準快照回填 claims；無快照時 core 會原樣返回 confidence。"""
    return tuple(
        claim.model_copy(
            update={
                "confidence": apply_latest(
                    project,
                    claim.confidence,
                    claim.concept.raw_text,
                )
            }
        )
        for claim in claims
    )


def process_media(
    project: Project,
    media_hash: str,
    concepts: list[Concept],
    *,
    provider: VisionProvider | None = None,
    task: str = "detect",
    now: datetime | None = None,
    id_factory: Callable[[], str] | None = None,
) -> ProcessOutcome:
    try:
        record = project.media.get(media_hash)
    except NotFoundError as exc:
        raise UnknownMediaError(f"media {media_hash[:12]} 不存在") from exc

    blob = project.blobs.find(media_hash)
    if blob is None:
        raise UnknownMediaError(f"media blob {media_hash[:12]} 不存在")

    active_provider = provider or FixtureProvider()
    capability = active_provider.capability
    request = InferenceRequest(concepts=tuple(concepts))
    start = time.perf_counter()
    result = active_provider.infer(blob.read_bytes(), request)
    calibrated_claims = apply_latest_to_claims(project, result.claims)
    duration_ms = 0 if now is not None else max(0, int((time.perf_counter() - start) * 1000))
    effective_now = now or datetime.now(timezone.utc)
    next_id = id_factory or _new_ulid
    run_id = next_id()
    persisted_claims = tuple(
        claim.model_copy(update={"claim_id": _claim_id_for_run(run_id, index)})
        for index, claim in enumerate(calibrated_claims)
    )
    producer = Producer(
        provider_id=capability.provider_id,
        provider_version=capability.version,
        params_hash=_params_hash(
            concepts=concepts,
            provider_id=capability.provider_id,
            task=task,
            version=capability.version,
        ),
    )
    subject = MediaSubject(
        media_hash=record.media_hash,
        width_px=record.width_px,
        height_px=record.height_px,
    )
    run = record_inference_run(
        project,
        subject=subject,
        producer=producer,
        task=task,
        claims=persisted_claims,
        duration_ms=duration_ms,
        run_id=run_id,
        decision_id=next_id(),
        cost_id=next_id(),
        outcome_id=next_id(),
        now=effective_now,
    )
    return ProcessOutcome(run=run)
