"""OpenAI 雲端 VLM provider（票-0017）。

本模組是 Provider adapter：呼叫 OpenAI Responses API，並把輸出正規化成 core Claim。
測試一律注入 fake client；預設 client 只在實際使用且未注入時才建立。
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from visionforge_core.contracts import BBox, Claim, Concept, Confidence, ProviderCapability
from visionforge_core.providers import InferenceRequest, InferenceResult

_PROVIDER_ID = "openai"
_CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_OPENAI_BASE_URL = "https://api.openai.com/v1"


class OpenAIProviderError(RuntimeError):
    """OpenAI provider 呼叫失敗；訊息不得洩漏金鑰。"""


class OpenAIVisionProvider:
    """OpenAI Responses API backed VisionProvider。"""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: object | None = None,
        base_url: str = _OPENAI_BASE_URL,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._client = client

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id=_PROVIDER_ID,
            version=self._model,
            role="teacher",
            locality="cloud",
            tasks=("detect",),
            promptable_by=("text",),
            reproducible=False,
            trainable=False,
            cost_profile="api_metered",
        )

    def infer(self, media_bytes: bytes, request: InferenceRequest) -> InferenceResult:
        if not request.concepts:
            return InferenceResult(claims=(), provider_id=_PROVIDER_ID)

        try:
            response = self._responses_create(media_bytes, request)
        except Exception as exc:  # noqa: BLE001 - provider boundary sanitizes all SDK errors.
            raise OpenAIProviderError(_sanitize_error(exc, self._api_key)) from exc

        return InferenceResult(
            claims=tuple(_claims_from_text(_response_text(response), request, self._model)),
            provider_id=_PROVIDER_ID,
        )

    def _responses_create(self, media_bytes: bytes, request: InferenceRequest) -> object:
        client = (
            self._client
            if self._client is not None
            else _default_client(self._api_key, self._base_url)
        )
        return client.responses.create(
            model=self._model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": _prompt(request)},
                        {
                            "type": "input_image",
                            "image_url": _data_url(media_bytes),
                            "detail": "auto",
                        },
                    ],
                }
            ],
            text={"format": _response_format()},
        )


def _default_client(api_key: str, base_url: str) -> object:
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=base_url)


def _prompt(request: InferenceRequest) -> str:
    concepts = [concept.raw_text for concept in request.concepts]
    return (
        "Find each requested concept in the image. "
        "Return only bounding boxes for visible instances. "
        "Coordinates must be normalized floats in [0, 1] as x1,y1,x2,y2. "
        "If a concept is absent, omit it. "
        f"Requested concepts: {json.dumps(concepts, ensure_ascii=False)}"
    )


def _response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "visionforge_detections",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "boxes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "concept": {"type": "string"},
                            "box": {
                                "type": "array",
                                "items": {"type": "number"},
                            },
                            "confidence": {"type": "number"},
                        },
                        "required": ["concept", "box", "confidence"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["boxes"],
            "additionalProperties": False,
        },
    }


def _data_url(media_bytes: bytes) -> str:
    encoded = base64.b64encode(media_bytes).decode("ascii")
    return f"data:{_media_type(media_bytes)};base64,{encoded}"


def _media_type(media_bytes: bytes) -> str:
    if media_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if media_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if media_bytes.startswith(b"RIFF") and media_bytes[8:12] == b"WEBP":
        return "image/webp"
    if media_bytes.startswith(b"BM"):
        return "image/bmp"
    if media_bytes.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    return "image/jpeg"


def _response_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text
    if isinstance(response, dict) and isinstance(response.get("output_text"), str):
        return response["output_text"]
    if isinstance(response, dict):
        for item in response.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return str(content.get("text", ""))
    return ""


def _claims_from_text(text: str, request: InferenceRequest, model: str) -> list[Claim]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict) or not isinstance(payload.get("boxes"), list):
        return []

    allowed = {concept.raw_text for concept in request.concepts}
    claims: list[Claim] = []
    for index, item in enumerate(payload["boxes"]):
        claim = _claim_from_item(item, index, allowed, model)
        if claim is not None:
            claims.append(claim)
    return claims


def _claim_from_item(
    item: object,
    index: int,
    allowed: set[str],
    model: str,
) -> Claim | None:
    if not isinstance(item, dict):
        return None
    concept = item.get("concept")
    box = item.get("box")
    confidence = item.get("confidence")
    if not isinstance(concept, str) or concept not in allowed:
        return None
    if not isinstance(box, list | tuple) or len(box) != 4:
        return None
    try:
        x1, y1, x2, y2 = (_clamp(float(value)) for value in box)
        raw = _clamp(float(confidence))
    except (TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    return Claim(
        claim_id=_stable_ulid(model, index, concept, (x1, y1, x2, y2), raw),
        assertion="presence",
        geometry=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
        concept=Concept(raw_text=concept),
        confidence=Confidence(raw=raw),
    )


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def _stable_ulid(model: str, index: int, concept: str, box: tuple[float, ...], raw: float) -> str:
    payload = json.dumps(
        {"box": box, "concept": concept, "index": index, "model": model, "raw": raw},
        ensure_ascii=False,
        sort_keys=True,
    )
    value = int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:16], "big")
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD32[value & 0b11111])
        value >>= 5
    return "".join(reversed(chars))


def _sanitize_error(exc: Exception, api_key: str) -> str:
    message = str(exc)
    if api_key:
        message = message.replace(api_key, "[redacted]")
    return f"OpenAI provider failed: {message}"
