"""VisionForge Vision Provider 實作套件（userland，ADR-0008）。

具體 provider（雲端 VLM、本地開放詞彙、可訓練學生）住這裡；
它們實作 core 的 provisional 介面 `visionforge_core.providers.VisionProvider`，
把原生輸出正規化成統一 Claim。依賴方向 providers→core（憲法 D13）。
"""

from visionforge_providers.fixture import FixtureProvider
from visionforge_providers.openai_vision import OpenAIProviderError, OpenAIVisionProvider

__all__ = ["FixtureProvider", "OpenAIProviderError", "OpenAIVisionProvider"]
