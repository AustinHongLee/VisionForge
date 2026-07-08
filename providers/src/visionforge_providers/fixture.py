"""確定性 fixture Vision Provider（票-0008）。

此 provider 不解碼影像、不碰網路，僅用穩定雜湊把概念轉成可重現的 Claim。
它的用途是把 providers→Claim→校準這條 userland 骨架跑通。
"""

from __future__ import annotations

import hashlib

from visionforge_core.contracts import BBox, Claim, Confidence, ProviderCapability
from visionforge_core.providers import InferenceRequest, InferenceResult

_PROVIDER_ID = "fixture"
_VERSION = "0.1.0"
_CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _digest_for(raw_text: str, index: int) -> bytes:
    return hashlib.sha256(f"{_PROVIDER_ID}\0{index}\0{raw_text}".encode()).digest()


def _unit(digest: bytes, offset: int) -> float:
    return int.from_bytes(digest[offset : offset + 2], "big") / 65_535


def _stable_ulid(digest: bytes) -> str:
    value = int.from_bytes(digest[:16], "big")
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD32[value & 0b11111])
        value >>= 5
    return "".join(reversed(chars))


def _bbox_from_digest(digest: bytes) -> BBox:
    width = 0.10 + _unit(digest, 0) * 0.25
    height = 0.10 + _unit(digest, 2) * 0.25
    x1 = _unit(digest, 4) * (1.0 - width)
    y1 = _unit(digest, 6) * (1.0 - height)
    return BBox(x1=x1, y1=y1, x2=x1 + width, y2=y1 + height)


def _confidence_from_digest(digest: bytes) -> Confidence:
    raw = 0.01 + _unit(digest, 8) * 0.98
    return Confidence(raw=raw)


class FixtureProvider:
    """可重現、零外部相依的第一個 Vision Provider。"""

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id=_PROVIDER_ID,
            version=_VERSION,
            role="teacher",
            locality="local",
            tasks=("detect",),
            promptable_by=("text",),
            reproducible=True,
            trainable=False,
            cost_profile="free_local",
        )

    def infer(self, media_bytes: bytes, request: InferenceRequest) -> InferenceResult:
        del media_bytes  # fixture 不解碼影像；保留參數以符合 provisional 介面。
        claims: list[Claim] = []
        for index, concept in enumerate(request.concepts):
            digest = _digest_for(concept.raw_text, index)
            claims.append(
                Claim(
                    claim_id=_stable_ulid(digest),
                    assertion="presence",
                    geometry=_bbox_from_digest(digest),
                    concept=concept,
                    confidence=_confidence_from_digest(digest),
                )
            )
        return InferenceResult(claims=tuple(claims), provider_id=_PROVIDER_ID)
