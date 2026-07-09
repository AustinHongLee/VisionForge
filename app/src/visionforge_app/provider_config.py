"""Provider 選擇與本機設定（票-0017）。

設定檔只在本機讀取，預設回 fixture，確保離線可用且金鑰不進 repo。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from visionforge_core.providers import VisionProvider
from visionforge_core.storage import Project
from visionforge_providers import FixtureProvider, OpenAIVisionProvider

DEFAULT_OPENAI_MODEL = "gpt-5-mini"
ENV_PROVIDER_CONFIG = "VISIONFORGE_PROVIDER_CONFIG"


class ProviderConfig(BaseModel):
    provider: str = "fixture"
    model: str = Field(default=DEFAULT_OPENAI_MODEL, min_length=1, max_length=128)
    openai_api_key: str | None = Field(default=None, min_length=1)


def load_provider(
    project: Project,
    *,
    client: object | None = None,
    config_path: Path | None = None,
) -> VisionProvider:
    """依本機 JSON 設定載入 provider；任何缺省或無效設定都回 fixture。"""
    config = _read_config(_provider_config_path(project, config_path))
    if config.provider != "openai" or not config.openai_api_key:
        return FixtureProvider()
    return OpenAIVisionProvider(api_key=config.openai_api_key, model=config.model, client=client)


def _provider_config_path(project: Project, override: Path | None) -> Path:
    if override is not None:
        return override
    configured = os.environ.get(ENV_PROVIDER_CONFIG)
    if configured:
        return Path(configured)
    return project.root / "provider-config.json"


def _read_config(path: Path) -> ProviderConfig:
    if not path.is_file():
        return ProviderConfig()
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        return ProviderConfig.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError, ValueError):
        return ProviderConfig()
