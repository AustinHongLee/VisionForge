"""Claim Schema v1.0 — 唯一事實來源（ADR-0003）。

本檔是核心與一切 Vision Provider 的唯一耦合點（憲法 PR2）。
JSON Schema 與 TypeScript 型別由本檔生成；文件與本檔不一致時，以本檔＋ADR-0003 為準。

憲法對照：
- PR2：schema_version 欄位；型別只增不改（N/N-1 相容策略）。
- PR6：Producer 三元組——任何 Claim 必可回答「你是誰的哪一版、用什麼提示產生的」。
- F1/F2：幾何為型別化開放聯集；未知型別保留不解讀（UnknownGeometry），不得丟棄。
- D3/D4：InferenceRun 的 decision_ref 與 cost_ref 必填——不存在無帳的調用。
- D7：Label 是獨立不可變記錄，唯一誕生途徑是審核狀態機；Claim 永遠保存 Provider 原始輸出。
- A5：本檔由 Pydantic 驗證，非法資料在邊界被拒——確定性優於寬容。
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0"

# 64 KB：provider_extra 硬上限（ADR-0003 裁決 #4）。裁剪是 adapter 正規化層的責任。
_PROVIDER_EXTRA_MAX_BYTES = 64 * 1024

# ---------------------------------------------------------------------------
# 基礎型別
# ---------------------------------------------------------------------------

# ULID（Crockford Base32，26 字元）：時間可排序的識別碼。
Ulid = Annotated[str, Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")]
# 內容雜湊（SHA-256 十六進位小寫）：媒體與 mask 的身分（R1 §5.4 內容雜湊定址）。
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
# 正規化座標：一律 0–1，像素基準由 MediaSubject 提供（草案 §3）。
UnitFloat = Annotated[float, Field(ge=0.0, le=1.0)]
# 登記名（provider/task/skeleton 等）：小寫 slug。
Slug = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")]


class StrictModel(BaseModel):
    """契約基底：拒絕未知欄位（A5）、實例不可變（帳本精神）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)


def _require_tz(v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError("時間戳必須帶時區（帳本的可重放性要求，D3/F7）")
    return v


# ---------------------------------------------------------------------------
# 幾何：型別化開放聯集（F1）
# ---------------------------------------------------------------------------


class Point(StrictModel):
    x: UnitFloat
    y: UnitFloat


class BBox(StrictModel):
    type: Literal["bbox"] = "bbox"
    x1: UnitFloat
    y1: UnitFloat
    x2: UnitFloat
    y2: UnitFloat

    @model_validator(mode="after")
    def _non_degenerate(self) -> BBox:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("bbox 必須有正面積（x2>x1 且 y2>y1）")
        return self


class Polygon(StrictModel):
    type: Literal["polygon"] = "polygon"
    points: tuple[Point, ...] = Field(min_length=3)


class MaskRef(StrictModel):
    """mask 本體不內嵌，走內容雜湊定址檔案（ADR-0003 裁決 #1：RLE/COCO）。"""

    type: Literal["mask_ref"] = "mask_ref"
    format: Literal["rle_coco"] = "rle_coco"
    mask_hash: Sha256


class KeypointPoint(StrictModel):
    x: UnitFloat
    y: UnitFloat
    visible: bool = True


class Keypoints(StrictModel):
    """骨架定義由任務模組擁有（ADR-0003 裁決 #3），此處只存登記名。"""

    type: Literal["keypoints"] = "keypoints"
    skeleton_ref: Slug
    points: tuple[KeypointPoint, ...] = Field(min_length=1)


class WholeImage(StrictModel):
    """圖級陳述（無幾何）；absence 斷言的唯一合法幾何。"""

    type: Literal["whole_image"] = "whole_image"


_KNOWN_GEOMETRY_TYPES = frozenset({"bbox", "polygon", "mask_ref", "keypoints", "whole_image"})


class UnknownGeometry(BaseModel):
    """前向相容（F1）：未知幾何型別保留原文、標記不可解讀，不得丟棄。

    注意：已知型別若格式錯誤，必須報錯而非落入本類——否則壞資料會偽裝成未來資料。
    """

    model_config = ConfigDict(extra="allow", frozen=True)
    type: str

    @field_validator("type")
    @classmethod
    def _must_be_truly_unknown(cls, v: str) -> str:
        if v in _KNOWN_GEOMETRY_TYPES:
            raise ValueError(f"'{v}' 是已知幾何型別，格式錯誤不得降級為 UnknownGeometry")
        return v

    @property
    def interpretable(self) -> bool:
        return False


Geometry = Annotated[
    BBox | Polygon | MaskRef | Keypoints | WholeImage | UnknownGeometry,
    Field(union_mode="left_to_right"),
]


# ---------------------------------------------------------------------------
# 概念：開放詞彙的落地（憲法附錄 #3；草案 §4）
# ---------------------------------------------------------------------------


class ConceptMappingProvenance(StrictModel):
    """「rusty bolt 算不算本專案的『鏽蝕』」——映射本身也是有出處的意見。"""

    kind: Literal["human", "rule", "model"]
    actor: str = Field(min_length=1, max_length=256)  # 人名／規則 id／provider_id@version
    mapped_at: datetime

    _tz = field_validator("mapped_at")(_require_tz)


class Concept(StrictModel):
    raw_text: str = Field(min_length=1, max_length=512)  # Provider 原話，永遠保存
    taxonomy_node_id: Ulid | None = None
    mapping_provenance: ConceptMappingProvenance | None = None

    @model_validator(mode="after")
    def _mapping_needs_provenance(self) -> Concept:
        if self.taxonomy_node_id is not None and self.mapping_provenance is None:
            raise ValueError("已映射至 taxonomy 的概念必須附映射出處（血統無死角）")
        return self


# ---------------------------------------------------------------------------
# 信心：原始與校準分離（憲法 §3 Confidence；R2 9.2 收縮估計）
# ---------------------------------------------------------------------------


class Reliability(str, Enum):
    none = "none"
    low = "low"
    high = "high"


class Confidence(StrictModel):
    """分流邏輯只准讀 calibrated；reliability 為 none/low 時憲法規定一律人審。"""

    raw: UnitFloat
    calibrated: UnitFloat | None = None
    calibration_ref: Ulid | None = None
    reliability: Reliability = Reliability.none

    @model_validator(mode="after")
    def _calibration_invariants(self) -> Confidence:
        if (self.calibrated is None) != (self.calibration_ref is None):
            raise ValueError("calibrated 與 calibration_ref 必須同時存在或同時缺席")
        if self.reliability is not Reliability.none and self.calibrated is None:
            raise ValueError("宣稱校準信賴度卻沒有校準值（P5：不可驗證的能力視同不存在）")
        return self


# ---------------------------------------------------------------------------
# 審核：Claim → Label 的唯一通道（D7）
# ---------------------------------------------------------------------------


class ReviewStatus(str, Enum):
    draft = "draft"
    queued_fast = "queued_fast"      # 快速確認佇列（校準高信心）
    queued_detail = "queued_detail"  # 逐張審核佇列
    queued_manual = "queued_manual"  # 人工重標佇列（含未校準之保守路由）
    approved = "approved"
    edited_approved = "edited_approved"
    rejected = "rejected"


_TERMINAL_REVIEW = frozenset(
    {ReviewStatus.approved, ReviewStatus.edited_approved, ReviewStatus.rejected}
)


class Review(StrictModel):
    status: ReviewStatus = ReviewStatus.draft
    reviewer: str | None = Field(default=None, max_length=256)
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def _terminal_needs_reviewer(self) -> Review:
        if self.status in _TERMINAL_REVIEW:
            if self.reviewer is None or self.reviewed_at is None:
                raise ValueError("終局審核狀態必須記載審核者與時間（P4：人為判斷必留痕）")
            _require_tz(self.reviewed_at)
        return self


# ---------------------------------------------------------------------------
# Claim 與 InferenceRun（草案 §2 兩層結構）
# ---------------------------------------------------------------------------


class Assertion(str, Enum):
    presence = "presence"
    absence = "absence"  # ADR-0003 裁決 #2：否定陳述是一等公民（黃金集需要已驗證的空圖）


class Claim(StrictModel):
    """單一實例的陳述。Claim 是有出處的意見，不是事實（憲法 §3）。"""

    claim_id: Ulid
    assertion: Assertion = Assertion.presence
    geometry: Geometry
    concept: Concept
    confidence: Confidence
    review: Review = Review()
    provider_extra: dict[str, Any] | None = None  # 不透明袋：核心不解讀、原樣保存

    @model_validator(mode="after")
    def _invariants(self) -> Claim:
        if self.assertion is Assertion.absence and not isinstance(self.geometry, WholeImage):
            raise ValueError("absence 斷言必須配 whole_image 幾何（ADR-0003 裁決 #2）")
        if self.provider_extra is not None:
            try:
                size = len(json.dumps(self.provider_extra, ensure_ascii=False).encode("utf-8"))
            except (TypeError, ValueError) as exc:
                raise ValueError("provider_extra 必須可 JSON 序列化") from exc
            if size > _PROVIDER_EXTRA_MAX_BYTES:
                raise ValueError(
                    f"provider_extra 超過 {_PROVIDER_EXTRA_MAX_BYTES} bytes 硬上限"
                    "（ADR-0003 裁決 #4：裁剪是 adapter 的責任）"
                )
        return self


class MediaSubject(StrictModel):
    """像素尺寸是 normalized 座標的換算基準——綁在 Run 上，杜絕座標系歧義。"""

    media_hash: Sha256
    width_px: int = Field(gt=0, le=1_000_000)
    height_px: int = Field(gt=0, le=1_000_000)


class Producer(StrictModel):
    """PR6：版本即身分。提示式 Provider 的 prompt_ref 必填由 adapter 層強制。"""

    provider_id: Slug
    provider_version: str = Field(min_length=1, max_length=128)
    params_hash: Sha256
    prompt_ref: Ulid | None = None


class InferenceRun(StrictModel):
    """一次 Provider 調用的批次紀錄。出處與成本記在 Run，審核以 Claim 為單位。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    run_id: Ulid
    subject: MediaSubject
    producer: Producer
    task: Slug  # 任務模組登記名（A9：核心任務不可知）
    created_at: datetime
    duration_ms: int = Field(ge=0)
    cost_ref: Ulid      # D4：不存在不入帳的調用路徑
    decision_ref: Ulid  # D3：每次調用都源自一筆可重放的 Orchestrator Decision
    claims: tuple[Claim, ...] = ()

    _tz = field_validator("created_at")(_require_tz)


# ---------------------------------------------------------------------------
# Label：經人審批准的事實（D7）
# ---------------------------------------------------------------------------


class Label(StrictModel):
    """不可變記錄；唯一誕生途徑是審核狀態機（服務層強制，本類記載其產物）。

    設計理由（ADR-0003）：Label 與 Claim 分離儲存，Claim 永遠保存 Provider 原始輸出，
    兩者對照即可量測 Provider 真實錯誤率——這是盲審與防線五的量測基礎。
    """

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    label_id: Ulid
    claim_ref: Ulid
    run_ref: Ulid
    media_hash: Sha256
    assertion: Assertion
    final_geometry: Geometry
    final_concept: Concept
    reviewer: str = Field(min_length=1, max_length=256)
    reviewed_at: datetime
    source_status: Literal["approved", "edited_approved"]

    _tz = field_validator("reviewed_at")(_require_tz)

    @model_validator(mode="after")
    def _label_invariants(self) -> Label:
        if isinstance(self.final_geometry, UnknownGeometry):
            raise ValueError("Label 的幾何必須可解讀——人不可能批准自己看不懂的東西")
        if self.assertion is Assertion.absence and not isinstance(
            self.final_geometry, WholeImage
        ):
            raise ValueError("absence Label 必須配 whole_image 幾何")
        if self.final_concept.taxonomy_node_id is None:
            raise ValueError("Label 必須映射至專案 Taxonomy（未映射的概念不能成為訓練資料）")
        return self
