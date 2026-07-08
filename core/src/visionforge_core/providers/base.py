"""Vision Provider 的 provisional 呼叫介面（ADR-0008）。

⚠ PROVISIONAL — 本介面**明確不凍結**（R2 §6.3「避免抽象災難」、A10 Rule of Two）。
介面的皺褶（各家座標系、信心語意、失敗模式）只有真實使用才暴露；接滿三個
真實 provider（雲端 VLM＋本地開放詞彙＋可訓練學生）並用到暴露皺褶後，才另開
ADR 固化。在此之前簽名可改，**不進凍結守門測試**。

輸出正規化＋校準才是本抽象最難最值錢的部分：adapter 把原生輸出翻成統一 Claim，
信心值一律走校準引擎（ADR-0007）。核心永不解讀像素（憲法 §4）。
具體 provider 實作屬 providers/（userland）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from visionforge_core.contracts import Claim, Concept, ProviderCapability


@dataclass(frozen=True)
class InferenceRequest:
    """要老師找什麼（開放詞彙）。provisional。"""

    concepts: tuple[Concept, ...] = ()
    prompt: str = ""


@dataclass(frozen=True)
class InferenceResult:
    """provider 一次調用的正規化輸出。provisional。"""

    claims: tuple[Claim, ...]
    provider_id: str
    diagnostics: dict[str, Any] = field(default_factory=dict)  # 原生診斷，核心不解讀


@runtime_checkable
class VisionProvider(Protocol):
    """輸入影像→輸出結構化理解。角色（teacher/student）由能力聲明與調用情境決定。"""

    @property
    def capability(self) -> ProviderCapability: ...

    def infer(self, media_bytes: bytes, request: InferenceRequest) -> InferenceResult: ...
