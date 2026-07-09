# 票-0017：第一個真實 provider——OpenAI 雲端 VLM

| 項目 | 內容 |
|---|---|
| 狀態 | 🟨 已發出（2026-07-08，ADR-0008「先接三個」的第一個真實 provider） |
| 承包 | Codex（Builder） |
| 審查層級 | **L2 必審**（首個網路呼叫 provider＋金鑰處理；**Architect 合併前審查**，協議 §3-2） |
| 政策依據 | ADR-0008（Provider 抽象、provisional 介面、漸進固化）、憲法 §7.3（離線本分） |

## 【目標】

接第一個真實老師：OpenAI 雲端 VLM。實作 `providers/` 的 `OpenAIVisionProvider`（實作 provisional `VisionProvider`），把影像＋要找的概念送 OpenAI、以 **Structured Outputs** 取回框、正規化成 `Claim`；app 依**設定檔**選 provider（預設仍 fixture）。**因 Provider 抽象就緒，這是 drop-in——不改 UI、不改審核/校準/匯出。**

## 【政策】（金鑰與離線，凍結）

1. **金鑰絕不進 repo／log**。放 gitignore 的 JSON 設定檔，執行時載入。
2. 設定路徑：env `VISIONFORGE_PROVIDER_CONFIG`，預設 `<project.root>/provider-config.json`。形狀：
   ```json
   { "provider": "openai", "model": "gpt-5-mini", "openai_api_key": "sk-..." }
   ```
   （`model` 由使用者填當前確切型號——目前小型 vision 選項：GPT-5 mini／nano、GPT-5.4 mini、GPT-4o mini。）
3. **離線優先（§7.3）**：無設定檔、或 `provider!="openai"`、或缺 key → 回退 **FixtureProvider**。產品在沒有雲端時完整可用。
4. 錯誤絕不外洩金鑰（例外訊息/日誌不得含 key）。

## 【範圍】（白名單）

`providers/**`（`OpenAIVisionProvider`＋`providers/pyproject.toml` 加 `openai` SDK）、`app/**`（設定載入＋provider 選擇工廠，接進 process_media／/infer）、根 `.gitignore`（忽略 `provider-config.json`）。測試於 `providers/tests/`、`app/tests/`。

**不得動**：`core/**`、`ui/**`、`.github/**`、`scripts/**`、根 `pyproject.toml`。

## 【介面】（消費 core 之 provisional 介面，不得改 core）

```python
# providers/src/visionforge_providers/openai_vision.py
class OpenAIVisionProvider:  # 需滿足 visionforge_core.providers.VisionProvider
    def __init__(self, *, api_key: str, model: str, client: object | None = None) -> None: ...
    #   client 可注入（測試用 fake；預設建 openai 官方 SDK client）
    @property
    def capability(self) -> ProviderCapability: ...
    def infer(self, media_bytes: bytes, request: InferenceRequest) -> InferenceResult: ...

# app：provider 工廠（依設定檔選）
def load_provider(project: Project) -> VisionProvider: ...   # 預設 FixtureProvider
```

能力聲明固定：`provider_id="openai"`、`version=model`、`role="teacher"`、`locality="cloud"`、`tasks=("detect",)`、`promptable_by=("text",)`、`reproducible=False`、`trainable=False`、`cost_profile="api_metered"`。

## 【工作項】

1. `OpenAIVisionProvider.infer`：base64 影像＋提示（要求對 `request.concepts` 逐一回報框），用 **Responses API＋Structured Outputs** 取回 JSON（每筆：概念、`box=[x1,y1,x2,y2]` 正規化 0–1、`confidence` 0–1）→ 正規化成 `Claim(geometry=BBox, concept=Concept(raw_text=概念), confidence=Confidence(raw=confidence))`。
2. **皺褶處理（R2 §6.3）**：VLM 框偏鬆/可能不合法——超界座標夾到 [0,1]、退化框（面積 0）丟棄、回應非法 JSON→回空 claims 不崩；API 錯誤→拋結構化 provider 例外（訊息不含 key）。
3. app `load_provider`：讀設定檔→`provider=="openai"` 且有 key→`OpenAIVisionProvider(...)`；否則 `FixtureProvider()`。process_media／/infer 改用 `load_provider(project)`（取代寫死 fixture）。
4. `.gitignore` 加 `provider-config.json`。
5. `providers/pyproject.toml` 加 `openai` SDK（釘版）。

## 【驗收】（測試清單＝完成的唯一定義；**不得在 CI 呼叫真 API**）

1. `isinstance(OpenAIVisionProvider(api_key="x", model="gpt-5-mini", client=fake), VisionProvider)`；capability 如上。
2. **注入 fake client** 回一段 canned JSON（2 個框）→ `infer` 回 2 個 Claim，concept/BBox/confidence 正確、座標在 [0,1]。
3. 退化/超界框 → 丟棄或夾值；非法 JSON → 回空 claims、不崩。
4. `load_provider`：無設定檔→FixtureProvider；設定 `provider=openai`+key（fake client 注入路徑）→OpenAIVisionProvider；`provider=fixture`→Fixture。
5. 金鑰不外洩：例外/日誌不含 key（測試斷言）。
6. `python scripts/check_forbidden_imports.py`、`ruff check app providers`、`pytest app/tests providers/tests` 全綠（無真 API）。

## 【憲法】

ADR-0008（provisional 介面，勿在此固化）、§7.3（離線優先、fixture 預設）、PR5（能力聲明）、D13（providers/app→core）、D14（結構化錯誤、皺褶容錯）、P5（reliability 仍由校準決定，本 provider 只報 raw）、A5（正規化盡量確定，但 VLM 本質非確定＝reproducible:false 已聲明）。

## 【禁區】

不得把金鑰寫進 repo／測試／日誌／例外訊息；不得在 CI 呼叫真 OpenAI API（一律 fake client）；不得改 `core/**`（含 provisional 介面簽名——有意見回報）；不得動 `ui/**`、`.github/**`、`scripts/**`、根 `pyproject.toml`；不得引入 openai 以外的新網路相依；規格衝突或缺件 → 停手回報，不腦補。

## 【交付物】

PR 一個（分支建議 `codex/ticket-0017-openai-provider`），說明含 D20 憲法聲明＋驗收勾選。**L2 票：CI 綠後仍需 Architect 合併前審查**（聚焦金鑰不外洩、離線 fallback、皺褶容錯、core 未被改）。合併後：決策者在 `provider-config.json` 填入 OpenAI 金鑰＋model，「看懂」站的框即由真老師畫。
