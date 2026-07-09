"""最小 Taxonomy 契約（ADR-0010）。

概念登記：raw_text → 穩定的 taxonomy_node_id。Label 的概念必須映射至節點
（Label 不變量：未映射的概念不能成為訓練資料）。這是最小骨架——豐富版
（概念卡／正反例／prompt 資產，R2 10.2 #4）延後（A10）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from visionforge_core.contracts.claims import SCHEMA_VERSION, StrictModel, Ulid, _require_tz


class TaxonomyNode(StrictModel):
    """專案 Taxonomy 的一個節點；概念的權威身分。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    node_id: Ulid
    raw_text: str = Field(min_length=1, max_length=512)
    created_at: datetime

    _tz = field_validator("created_at")(_require_tz)
