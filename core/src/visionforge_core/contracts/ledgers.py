"""帳本 Schema v1.0 — Decision／Cost／ReviewEvent／版本 Manifest（ADR-0004）。

憲法 B1：「可以晚做聰明，不可以晚做誠實。」路由邏輯允許極簡，但這些記錄格式
必須從第一天完整——缺頁的帳本永遠補不回來。

憲法對照：
- D3 ：DecisionRecord 記到可重放的程度；重放讀已記錄的輸出，不重新調用機率性元件。
- D4 ：CostEntry——不存在不入帳的調用路徑；本地也計量（C1）。
- C5 ：人工是最貴的 Provider——human review 的時間同樣入帳。
- C6 ：預測必可證偽——estimate 與 actual 分錄配對留存。
- F3 ：計量單位可插拔——CostMeasurement.unit 是開放登記名，不綁 token 或任何幣別。
- D5 ：Dataset 版本 = Manifest；回滾 = 以舊版為 parent 開新版，永不就地修改。
- D8 ：GoldenSetEntry 永不出現在 DatasetVersionManifest 的 split 中。
- P4 ：ReviewEvent——每一次人為判斷都留痕（含否決）；盲審/蜜罐 context 是防線五的資料來源。
- A12：human_override 是一種 DecisionRecord——人可覆寫一切，覆寫本身也入帳。

儲存層可將大型 Manifest 正規化為關聯表；本檔定義的是邏輯與交換格式（唯一事實來源）。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_serializer, field_validator, model_validator

from visionforge_core.contracts.claims import (
    SCHEMA_VERSION,
    ReviewStatus,
    Sha256,
    Slug,
    StrictModel,
    Ulid,
    UnitFloat,
    _require_tz,
)

# ---------------------------------------------------------------------------
# 通用參照
# ---------------------------------------------------------------------------

RefKind = Literal[
    "media",
    "claim",
    "run",
    "label",
    "dataset_version",
    "golden_entry",
    "batch",
    "report",
    "calibration",
    "cost",
    "decision",
    "review_event",
    "training_run",
    "export_job",
    "data_job",
]


class InputRef(StrictModel):
    """異質參照：帳本之間互相指認的統一形式。"""

    kind: RefKind
    id: str = Field(min_length=1, max_length=128)


# ---------------------------------------------------------------------------
# Decision 帳本（D3、O1–O10、A12）
# ---------------------------------------------------------------------------

DecisionKind = Literal[
    "invoke_provider",  # 選擇讓某 Provider 處理某輸入
    "route_claim",      # 校準信心分流至審核佇列（O2；永不直接產生 Label）
    "escalate_human",   # 移交人工（O5 封閉觸發清單）
    "cache_reuse",      # 快取重用（O9）
    "gate_verdict",     # 入庫閘門裁決
    "human_override",   # 人為覆寫（A12：覆寫必勝且入帳）
]

# 理由碼登記表：封閉集合，擴充＝修訂本表（deterministic 驗證優於自由文字）。
REASON_CODES: frozenset[str] = frozenset(
    {
        # 路由
        "audition_best",      # 試鏡成績最佳
        "only_capable",       # 唯一具能力的 Provider
        "cheapest_capable",   # 最便宜且具能力（C4 升級鏈起點）
        "cache_valid",        # 三元組未變，快取有效
        # 分流
        "calibrated_high",    # 校準信心達標 → 快速佇列
        "calibrated_low",     # 校準信心不足 → 細審/人工
        "uncalibrated",       # 未校準 → 憲法規定一律人審
        # 升級/移交（O5 封閉清單）
        "budget_exhausted",
        "providers_disagree",
        "policy_mandate",
        "novel_input",
        "audit_failure",
        "user_request",
        # 閘門
        "gate_pass",
        "gate_fail_statistical",
        "gate_fail_golden",
        # 覆寫
        "human_judgment",
    }
)


class PolicyRef(StrictModel):
    """生效政策的快照參照——重放時必須能指認當時的政策（D3）。"""

    policy_hash: Sha256
    policy_label: str = Field(min_length=1, max_length=128)


class CandidateProvider(StrictModel):
    """候選 Provider 的證據列（A6：沒有證據的選擇等於沒發生）。"""

    provider_id: Slug
    provider_version: str = Field(min_length=1, max_length=128)
    capability_ok: bool
    audition_score: UnitFloat | None = None
    estimated_cost_ref: Ulid | None = None
    rejected_reason: Slug | None = None


class DecisionChoice(StrictModel):
    target: str = Field(min_length=1, max_length=256)  # provider_id@ver／佇列名／裁決結果
    reason_code: str

    @field_validator("reason_code")
    @classmethod
    def _registered(cls, v: str) -> str:
        if v not in REASON_CODES:
            raise ValueError(f"未登記的理由碼「{v}」——擴充請修訂 REASON_CODES（確定性優於自由文字）")
        return v


class DecisionRecord(StrictModel):
    """Orchestrator 的不可變決策記錄。五不變量（憲法 §4.4）：
    源自政策、附證據、經計量、可重放、可被人覆寫——前四者由本結構承載，
    第五者由 kind=human_override 的新記錄實現（不修改原記錄）。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    decision_id: Ulid
    at: datetime
    kind: DecisionKind
    actor: str = Field(default="orchestrator", min_length=1, max_length=256)
    policy: PolicyRef
    inputs: tuple[InputRef, ...] = Field(min_length=1)
    candidates: tuple[CandidateProvider, ...] = ()
    choice: DecisionChoice
    evidence_refs: tuple[InputRef, ...] = ()
    overrides_ref: Ulid | None = None

    _tz = field_validator("at")(_require_tz)

    @model_validator(mode="after")
    def _invariants(self) -> DecisionRecord:
        if self.kind == "human_override":
            if self.overrides_ref is None:
                raise ValueError("human_override 必須指向被覆寫的原決策（A12：覆寫入帳）")
            if self.actor == "orchestrator":
                raise ValueError("human_override 的 actor 必須是人，不得是 orchestrator")
        elif self.overrides_ref is not None:
            raise ValueError("只有 human_override 可以帶 overrides_ref")
        if self.kind == "invoke_provider" and not self.candidates:
            raise ValueError("invoke_provider 必須列出候選清單（A6：選擇要有證據）")
        return self


class DecisionOutcome(StrictModel):
    """決策的實際結果——獨立追加記錄（append-only：結果不回寫原決策）。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    outcome_id: Ulid
    decision_ref: Ulid
    at: datetime
    status: Literal["success", "failure", "cancelled", "partial"]
    detail: str = Field(default="", max_length=1024)
    produced_refs: tuple[InputRef, ...] = ()

    _tz = field_validator("at")(_require_tz)


# ---------------------------------------------------------------------------
# Cost 帳本（C1–C8、D4、F3）
# ---------------------------------------------------------------------------


class CostAgent(StrictModel):
    """誰產生了這筆消耗——Provider 或人（C5：人工有價）。"""

    kind: Literal["provider", "human"]
    id: str = Field(min_length=1, max_length=128)
    version: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def _provider_needs_version(self) -> CostAgent:
        if self.kind == "provider" and not self.version:
            raise ValueError("provider 消耗必須記版本（PR6：版本即身分）")
        return self


class CostMeasurement(StrictModel):
    """計量單位可插拔（F3）：unit 是登記名（usd／twd／tokens_in／seconds／gpu_seconds…）。

    金額用 Decimal 並以字串序列化——錢進浮點數是十年後對不了帳的經典錯誤。"""

    unit: Slug
    amount: Decimal = Field(ge=0)

    @field_serializer("amount")
    def _exact(self, v: Decimal) -> str:
        return format(v, "f")


class CostEntry(StrictModel):
    """一筆消耗分錄。estimate 與 actual 是兩筆獨立分錄，actual 以 estimate_ref
    回指配對——預測必可證偽（C6），對帳查詢由此成立。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    cost_id: Ulid
    at: datetime
    phase: Literal["estimate", "actual"]
    subject: InputRef
    agent: CostAgent
    measurements: tuple[CostMeasurement, ...] = Field(min_length=1)
    estimate_ref: Ulid | None = None

    _tz = field_validator("at")(_require_tz)

    @model_validator(mode="after")
    def _phase_invariants(self) -> CostEntry:
        if self.phase == "estimate" and self.estimate_ref is not None:
            raise ValueError("estimate 分錄不得帶 estimate_ref（它自己就是預估）")
        return self


# ---------------------------------------------------------------------------
# ReviewEvent 帳本（P4、D7、防線五）
# ---------------------------------------------------------------------------


class ReviewEvent(StrictModel):
    """一次人為審核動作。Label 記結果，ReviewEvent 記行為——含否決與盲審。

    context=blind_audit／honeypot 是防線五的量測資料：盲審比對估計漏網錯誤率，
    蜜罐量測審核者當下狀態（R1 §9.3）。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    event_id: Ulid
    at: datetime
    actor: str = Field(min_length=1, max_length=256)
    claim_ref: Ulid
    from_status: ReviewStatus
    to_status: ReviewStatus
    label_ref: Ulid | None = None
    context: Literal["normal", "blind_audit", "honeypot"] = "normal"
    duration_ms: int | None = Field(default=None, ge=0)

    _tz = field_validator("at")(_require_tz)

    @model_validator(mode="after")
    def _invariants(self) -> ReviewEvent:
        if self.from_status == self.to_status:
            raise ValueError("審核事件必須改變狀態（無變化的事件是噪音）")
        approved = {ReviewStatus.approved, ReviewStatus.edited_approved}
        if self.to_status in approved and self.label_ref is None:
            raise ValueError("批准必須產生 Label 並回指（D7：批准是 Label 唯一的出生通道）")
        if self.to_status not in approved and self.label_ref is not None:
            raise ValueError("未批准的事件不得帶 label_ref")
        return self


# ---------------------------------------------------------------------------
# Dataset 版本 Manifest（D5）與黃金集登記（D8）
# ---------------------------------------------------------------------------


class ManifestEntry(StrictModel):
    media_hash: Sha256
    label_refs: tuple[Ulid, ...] = ()  # 空 = 純背景負樣本（健檢 #11 依賴）
    split: Literal["train", "val"]


class ProvenanceSummary(StrictModel):
    """血統成分表（防線二）：本版資料的出身統計快照。"""

    human: int = Field(ge=0)
    machine_assisted: int = Field(ge=0)
    imported: int = Field(ge=0)


class DatasetVersionManifest(StrictModel):
    """一個 Dataset 版本 = 一份清單，不是一份拷貝。回滾 = 以任一舊版為 parent
    開新版；歷史版本永不修改、永不刪除（D5）。黃金集項目不得出現在此（D8）。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    version_id: Ulid
    version_number: int = Field(ge=1)
    created_at: datetime
    parent_ref: Ulid | None = None
    entries: tuple[ManifestEntry, ...]
    provenance: ProvenanceSummary
    gate_decision_ref: Ulid | None = None  # 通過閘門的裁決；純匯入的第一版可為空
    note: str = Field(default="", max_length=512)

    _tz = field_validator("created_at")(_require_tz)

    @model_validator(mode="after")
    def _no_duplicate_media(self) -> DatasetVersionManifest:
        hashes = [e.media_hash for e in self.entries]
        if len(hashes) != len(set(hashes)):
            raise ValueError("同一版本內不得有重複媒體（版本完整性）")
        return self


class GoldenSetEntry(StrictModel):
    """黃金集登記：只增與除役，永不刪除；且永不進入任何訓練 manifest（D8）。"""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    entry_id: Ulid
    media_hash: Sha256
    label_ref: Ulid
    added_by: str = Field(min_length=1, max_length=256)
    added_at: datetime
    status: Literal["active", "retired"] = "active"
    retired_reason: str | None = Field(default=None, max_length=512)

    _tz = field_validator("added_at")(_require_tz)

    @model_validator(mode="after")
    def _retire_needs_reason(self) -> GoldenSetEntry:
        if self.status == "retired" and not self.retired_reason:
            raise ValueError("除役黃金樣本必須記理由（度量衡原器的變動要留痕）")
        if self.status == "active" and self.retired_reason is not None:
            raise ValueError("active 樣本不得帶除役理由")
        return self
