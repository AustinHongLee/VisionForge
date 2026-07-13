"""Provider 選擇與本機設定（票-0017）。

設定檔只在本機讀取，預設回 fixture，確保離線可用且金鑰不進 repo。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from visionforge_core.providers import VisionProvider
from visionforge_core.storage import Project
from visionforge_providers import FixtureProvider, OpenAIVisionProvider

DEFAULT_OPENAI_MODEL = "gpt-5-mini"
ENV_PROVIDER_CONFIG = "VISIONFORGE_PROVIDER_CONFIG"
ENV_DEVELOPER_FIXTURE = "VISIONFORGE_DEV_FIXTURE"


class ProviderConfigurationError(RuntimeError):
    """正式模式沒有可用 Teacher；不得靜默顯示不看圖片的 fixture 假框。"""


class ProviderConfig(BaseModel):
    provider: Literal["fixture", "openai"]
    model: str = Field(default=DEFAULT_OPENAI_MODEL, min_length=1, max_length=128)
    openai_api_key: str | None = Field(default=None, min_length=1)


def load_provider(
    project: Project,
    *,
    client: object | None = None,
    config_path: Path | None = None,
) -> VisionProvider:
    """依明示設定載入 Teacher；fixture 只允許設定檔或 Developer Mode 明示。"""
    path = _provider_config_path(project, config_path)
    config = _read_config(path)
    if config is None:
        if os.environ.get(ENV_DEVELOPER_FIXTURE) == "1":
            return FixtureProvider()
        raise ProviderConfigurationError(
            f"未設定 Teacher（缺 {path.name}）；請設定 OpenAI，或在 Developer Mode 明示 fixture"
        )
    if config.provider == "fixture":
        return FixtureProvider()
    if not config.openai_api_key:
        raise ProviderConfigurationError("OpenAI Teacher 設定缺少 openai_api_key")
    return OpenAIVisionProvider(api_key=config.openai_api_key, model=config.model, client=client)


def _provider_config_path(project: Project, override: Path | None) -> Path:
    if override is not None:
        return override
    configured = os.environ.get(ENV_PROVIDER_CONFIG)
    if configured:
        return Path(configured)
    return project.root / "provider-config.json"


def _read_config(path: Path) -> ProviderConfig | None:
    if not path.is_file():
        return None
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        return ProviderConfig.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise ProviderConfigurationError(f"Teacher 設定無效：{exc}") from exc
