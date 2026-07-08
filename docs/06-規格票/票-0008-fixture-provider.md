# 票-0008：第一個 Vision Provider（確定性 fixture）

| 項目 | 內容 |
|---|---|
| 狀態 | 🟨 已發出（2026-07-08，並行雙軌） |
| 承包 | Codex（Builder） |
| 審查層級 | **L0 免審**（providers/ 白名單；套件與 CI job 已由 Architect 建好；CI 全綠＋D20 即由決策者合併） |
| 政策依據 | ADR-0008（Provider 抽象）；實作 core 之 provisional 介面 `visionforge_core.providers.VisionProvider` |

## 【目標】

在 `providers/` 落第一個 provider——**確定性 fixture**：實作 provisional 介面，對請求的每個 Concept 產生一個正規化 `Claim`（固定、可重現、零外部相依）。目的是把「provider → 正規化 Claim → 校準」這條路端到端走通、可測，作為之後接真雲端 VLM 的骨架。**不接網路、不裝影像庫、不碰 core。**

## 【範圍】（白名單）

`providers/**`（套件與 CI job 已由 Architect 建好）。實作 `providers/src/visionforge_providers/fixture.py`、於套件 `__init__` 匯出、測試於 `providers/tests/`。

**不得動**：`core/**`、根 `pyproject.toml`、`providers/pyproject.toml`（相依已凍結，fixture 不需新相依）、`.github/**`、`scripts/**`。

## 【介面】（消費 core 的 provisional 介面——不得改 core 簽名）

```python
# 來自 visionforge_core.providers（provisional，勿依賴其穩定性；有意見回報）
class VisionProvider(Protocol):
    @property
    def capability(self) -> ProviderCapability: ...
    def infer(self, media_bytes: bytes, request: InferenceRequest) -> InferenceResult: ...

# InferenceRequest(concepts: tuple[Concept,...]=(), prompt: str="")
# InferenceResult(claims: tuple[Claim,...], provider_id: str, diagnostics: dict={})

# 待實作
class FixtureProvider:  # 需滿足 VisionProvider（runtime_checkable）
    @property
    def capability(self) -> ProviderCapability: ...
    def infer(self, media_bytes: bytes, request: InferenceRequest) -> InferenceResult: ...
```

能力聲明固定為：`provider_id="fixture"`、`version="0.1.0"`、`role="teacher"`、`locality="local"`、`tasks=("detect",)`、`promptable_by=("text",)`、`reproducible=True`、`trainable=False`、`cost_profile="free_local"`。

## 【工作項】

1. `FixtureProvider.capability` 回上述固定 `ProviderCapability`。
2. `infer`：對 `request.concepts` 的**每個** Concept 產生一個 `Claim`（`assertion="presence"`、`geometry=BBox`、`concept=` 該 Concept、`confidence=Confidence(raw=…)`）：
   - **確定性**：座標與 raw 信心由 `Concept.raw_text`（＋其序號）以穩定雜湊推導（如 `hashlib.sha256`），映射到合法 `BBox`（`0≤x1<x2≤1`、`0≤y1<y2≤1`）與 `raw∈(0,1)`。同輸入永遠同輸出。
   - `claim_id`：由 `(provider_id, raw_text, 序號)` 穩定推出合法 ULID（26 碼 Crockford Base32）。
   - `media_bytes` 可忽略內容（fixture 不解碼），但不得因空/任意 bytes 崩潰。
3. `request.concepts` 為空 → 回 `InferenceResult(claims=(), ...)`。
4. `provider_id` 回 `"fixture"`；`diagnostics` 可留 `{}` 或放固定除錯資訊。

## 【驗收】（測試清單＝完成的唯一定義）

1. `isinstance(FixtureProvider(), VisionProvider)` 為真（runtime_checkable）。
2. `capability` 欄位如上；`ProviderCapability` 建構通過（無 ValidationError）。
3. **確定性**：同一 `(media_bytes, request)` 連呼叫兩次 → 兩個 `InferenceResult` 相等（claims 逐欄相同）。
4. 每個請求 Concept 對到一個 Claim，`concept.raw_text` 一致、`BBox` 合法、`confidence.raw∈(0,1)`。
5. 空 concepts → `claims=()`，不拋例外；任意/空 `media_bytes` 不崩潰。
6. **端到端**：把回傳 claims 當作已驗證觀測（`CalibrationObservation(concept_key=raw_text, raw=confidence.raw, correct=True)`）餵給 `visionforge_core.calibration.calibrate(...)`，再 `apply_calibration` 一個 Confidence → 不拋例外、回傳合法 `Confidence`（證明 provider→校準路徑通）。
7. `python scripts/check_forbidden_imports.py`、`ruff check providers`、`pytest providers/tests` 全綠。

## 【憲法】

ADR-0008（Provider 抽象、provisional 介面）、憲法 §3（Provider/Teacher/能力聲明）、A5（fixture 確定性）、D13（依賴方向 providers→core，不得反向）、A10（這是「先接三個」的第一個；介面皺褶留待真實 provider 暴露，勿在此固化）。

## 【禁區】

不得改 `core/**`（含 provisional 介面簽名——有意見回報，不動手）；不得動根/providers 的 `pyproject.toml`、`.github/**`、`scripts/**`；不得引入任何第三方相依（fixture 純標準庫）；不得接網路或解碼影像；規格衝突或缺件 → 停手回報，不腦補。

## 【交付物】

PR 一個（分支建議 `codex/ticket-0008-fixture-provider`），說明含 D20 憲法聲明＋驗收勾選。**L0 票：CI 綠即可由決策者直接合併**（若動到 `core/**` 或守門路徑則自動升 L2；pr-scope job 會標示層級）。
