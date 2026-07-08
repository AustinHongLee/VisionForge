"""Vision Provider 能力聲明契約（ADR-0008）。

能力聲明是宣告式 metadata、相對穩定，因此落為契約（進 JSON Schema/TS 管線）；
UI 依它動態組裝可用功能（憲法 §3、PR5：聲明是履歷，試鏡才是面試）。

對比：呼叫（invoke）介面的皺褶只有真實使用才暴露，故保持 provisional，
不放在此契約層——見 `visionforge_core.providers.base`（明標不凍結，A10）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from visionforge_core.contracts.claims import SCHEMA_VERSION, Slug, StrictModel

# 角色非身分：同一 Provider 可於不同調用扮演老師/學生（憲法 §3）。
ProviderRole = Literal["teacher", "student"]
Locality = Literal["local", "cloud"]
# 封閉集：新任務＝修訂本型別（確定性優於寬容，A5）。
VisionTask = Literal["detect", "segment", "classify", "describe", "ocr", "keypoints"]
PromptMode = Literal["text", "box", "point", "example", "none"]
CostProfile = Literal["free_local", "local_compute", "api_metered", "api_flat"]


class ProviderCapability(StrictModel):
    """Provider 機器可讀的能力自我聲明；路由與 UI 組裝的依據。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    provider_id: Slug
    version: str = Field(min_length=1, max_length=64)  # provider 自身版本
    role: ProviderRole
    locality: Locality
    tasks: tuple[VisionTask, ...] = Field(min_length=1)  # 支援任務，非空
    promptable_by: tuple[PromptMode, ...] = Field(min_length=1)  # 可被什麼提示
    reproducible: bool  # 同輸入是否同輸出（雲端 VLM 常為 False）
    trainable: bool  # 是否為可訓練學生
    cost_profile: CostProfile

    @field_validator("tasks", "promptable_by")
    @classmethod
    def _no_duplicates(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if len(v) != len(set(v)):
            raise ValueError("能力集合不得有重複項")
        return v
