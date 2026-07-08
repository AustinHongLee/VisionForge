"""Vision Provider 抽象（ADR-0008）：provisional 呼叫介面。

能力聲明契約在 `contracts.providers`（穩定、已 schema 化）；
本套件是 provisional 介面（不凍結，A10 接滿三家再固化）。
"""

from visionforge_core.providers.base import (
    InferenceRequest,
    InferenceResult,
    VisionProvider,
)

__all__ = ["InferenceRequest", "InferenceResult", "VisionProvider"]
