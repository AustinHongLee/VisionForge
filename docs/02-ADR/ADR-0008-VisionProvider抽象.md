# ADR-0008：採用 Vision Provider 抽象（能力聲明契約 ＋ 漸進固化紀律）

| 項目 | 內容 |
|---|---|
| 編號 | ADR-0008 |
| 日期 | 2026-07-08 |
| 狀態 | 🟨 提案（合併含本 ADR 的 commit 即視同採納；有異議回報即改） |
| 決策者 | 李宗鴻（Claude 起草） |

## 背景

R2 問題六是本輪評審**唯一全票通過**的提案：Provider＝任何「輸入影像→輸出結構化理解」的元件，本地雲端、可否訓練一視同仁，其上做師生二分。憲法 §3 已把 Vision Provider／Provider Capability／Teacher／Student／試鏡列為憲法級名詞。老師草稿（M0 的 10 分鐘 TTFV）與成本路由、Copilot 視覺工具全部站在這個抽象上。

**但 R2 §6.3 同時下了一條反面警告：「第一天就設計九家 Provider 的完美介面＝死於抽象。」** 介面的皺褶（VLM 回框偏鬆、各家座標系與信心語意不同、失敗模式各異）只有真實使用才會暴露；**抽象裡最難最值錢的是輸出正規化與校準層，不是介面定義本身。** 這與 A10／D12（Rule of Two：抽象須有兩個真實實作方可固化）完全一致。上一輪口頭說的「凍結 Provider 協定」若照字面執行，正是這條反面路徑——本 ADR 予以更正。

## 決策

採用 Provider 抽象，但**介面漸進固化、不預先凍結**。分三層落地：

1. **能力聲明（ProviderCapability）落為契約**——相對穩定、可先固化的宣告式 metadata：`provider_id`、`version`、`role`（teacher/student，**角色非身分**）、`locality`（local/cloud）、`tasks`（detect/segment/classify/describe/ocr…封閉集）、`promptable_by`（text/box/point/example/none 之集合）、`reproducible`（bool）、`trainable`（bool）、`cost_profile`。UI 依聲明**動態組裝**可用功能（憲法 §3、PR5：聲明是履歷，試鏡才是面試）。

2. **invoke 介面保持 provisional（明標非凍結）**——定義最小協定，例如 `infer(media_bytes, request) -> InferenceResult`（`InferenceResult` 攜 `Claim` 序列＋原生診斷）。此介面**不進凍結守門、簽名可改**，直到接滿三個真實 provider（一雲端 VLM＋一本地開放詞彙偵測器＋一可訓練學生，R2 §6.3）並用到暴露皺褶後，才另開 ADR 固化（Rule of Two/Three）。

3. **輸出正規化＋校準是本抽象的核心工作**（§6.3）——每個 provider 的 adapter 負責把原生輸出翻成統一 `Claim`（座標系、信心語意、失敗模式正規化）；信心值一律走已建的校準引擎（ADR-0007）產生 `calibrated`／`reliability`。核心永不解讀像素（憲法 §4）。

**地盤**：能力聲明契約與 provisional 介面屬 `core`（Architect）；具體 provider 實作屬 `providers/`（userland，Codex L0 票）。試鏡（Teacher Audition，黃金集實測給路由資格，PR5）是 kernel，另立。

## 理由

- 直接落實 R2 §6.1/6.2/6.3：唯一能同時容納 AI 草稿、成本路由、Copilot 視覺工具的地基；授權與廠商風險的保險（換 Provider 而非重寫）；敘事升級為「視覺能力調度者」。
- **守 A10/D12**：宣告式的能力聲明相對穩定，可先固化；行為式的 invoke 皺褶留給真實使用，滿三家再固化，避免抽象災難。
- 把最難的部分（正規化＋校準）擺正為核心工作，而非空轉在介面美學上。

## 曾考慮的替代方案

- **第一天凍結完整 Provider Protocol** → 棄：R2 §6.3 明警「死於抽象」；違 A10。
- **沿用 R1 Engine Adapter（只抽象可訓練模型）** → 棄：只涵蓋視覺能力的一半（R2 §6.1）。
- **不做抽象、直接寫死一個 VLM** → 棄：授權/廠商漲價停服無保險，敘事停在「訓練工具」（R2 §6.2）。
- **能力聲明也保持 provisional** → 棄：宣告式 metadata 夠穩定，先固化能讓 UI 動態組裝有依據；真正易變的是 invoke 行為。

## 影響範圍

- **新增**：`core/contracts/providers.py`（`ProviderCapability` 等能力聲明契約，進 JSON Schema/TS 管線）；`core` 一個 **provisional** 介面模組（非契約、不 schema 匯出、檔頭明標「provisional，勿凍結守門」）。
- **消費既有**：`Claim`/`Confidence`（provider 輸出正規化目標）、校準引擎（ADR-0007）。
- **開啟**：`providers/` 的實作票（Codex L0）。
- **相關 ADR**：ADR-0003（Claim 唯一事實來源）、ADR-0007（校準）。屬擴充，無牴觸。

## 憲法檢核（D19／D20）

- **觸及條文**：憲法 §3（Provider/Capability/Teacher/Student 定義）、§4（核心不解讀像素、Orchestrator 調度）、PR5（能力是履歷、試鏡是面試）、A10/D12（Rule of Two：抽象須兩實作方固化）、P5（能力聲明須可驗證＝試鏡）。
- **合規聲明**：本 ADR 未修改憲法條文或既有凍結契約；新增能力聲明契約與 provisional 介面，且明確以 A10 約束固化時機，正面履行 D12。師生二分依憲法「角色非身分」落地。
- **未牴觸**，無需修憲。惟若採納後出現新跨文件結構名（如 `ProviderCapability`／`InferenceResult`）→ 依治理義務登記入 `01-定義/名詞定義表.md`（修法，須李宗鴻明示同意，如 ADR-0007 前例）。

## 後續行動

1. 【Architect】採納後：`core` 新增 `ProviderCapability` 契約 ＋ provisional `infer` 介面（明標非凍結）→ 重生 schema/TS。
2. 【Codex，L0】第一個 provider 實作票（`providers/` 白名單）：建議先接一個**確定性 fixture／本地開放詞彙 stub** 把「provider → 正規化 Claim → 校準 → 審核佇列」端到端走通，成本為零、可測。
3. 【Codex，L0】緊接**第一個真實 provider**（雲端 VLM 或 Grounding DINO）以暴露真實皺褶；**固化在第三個真實 provider 之後**（另開 ADR）。
4. 【Architect】試鏡引擎（黃金集實測 → 路由資格；接校準引擎與帳本）。
5. 【李宗鴻】若採納且新增跨文件結構名 → 確認登記入 01-定義（修法）。
