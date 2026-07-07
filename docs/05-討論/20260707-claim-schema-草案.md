# Claim Schema 草案（v0.1）

> **⬛ 文件狀態：已歸檔** — 2026-07-07 定案畢業。**已落地於：ADR-0003（決策）＋ `core/src/visionforge_core/contracts/claims.py`（可執行契約，唯一事實來源）**。五個開放問題之裁決見 ADR-0003。本檔留底供考古，不得作為依據。

## 一、設計目標

Claim Schema 要同時伺候三個主人：2026 年的 Grounding DINO（回傳框）、未來的未知模型（回傳未知幾何，F1/F2）、以及十年後還要能重放的帳本（D3、F7）。因此原則是：**信封穩定、內容開放、出處完整。**

## 二、兩層結構：InferenceRun 與 Claim

一次 Provider 調用產生一筆 **InferenceRun**（批次紀錄），內含 0..N 筆 **Claim**（單實例陳述）。拆兩層的理由：出處與成本屬於「這一次調用」（記在 Run，不必每框重複），而審核與批准以「單一實例」為單位（憲法：Label = 經批准的 Claim），粒度必須到框。

```
InferenceRun
├─ run_id: ULID
├─ schema_version: "0.1"
├─ subject: { media_hash: sha256, width_px, height_px }   ← 綁像素尺寸，防座標系歧義
├─ producer: { provider_id, provider_version, params_hash, prompt_ref }   ← PR6：可回答「你是誰的哪一版」
├─ task: "detect"（任務模組登記名，A9）
├─ created_at, duration_ms
├─ cost_ref: 帳本條目 ID（明細在 Cost Engine，這裡只留參照）
├─ decision_ref: 觸發本次調用的 Orchestrator Decision ID（D3 的鏈）
└─ claims: [Claim, ...]

Claim
├─ claim_id: ULID
├─ geometry: 型別化聯集（見三）
├─ concept: { raw_text, taxonomy_node_id?, mapping_provenance }（見四）
├─ confidence: { raw, calibrated?, calibration_ref?, reliability }（見五）
└─ review: { status, reviewer, reviewed_at, edit_delta? }（見六）
```

## 三、幾何：型別化開放聯集（F1）

座標一律 **normalized 0–1**（浮點），像素尺寸由 Run.subject 提供換算基準。理由：媒體縮放、縮圖預覽、不同解析度重推論時，normalized 座標不變。

v0.1 只定義五型：`bbox`（x1,y1,x2,y2）、`polygon`（點列）、`mask_ref`（外部檔參照＋格式標記）、`keypoints`（點列＋骨架定義由任務模組擁有）、`whole_image`（圖級陳述，無幾何）。新幾何型別**只增不改**（PR9 同精神）；讀到未知型別的舊核心必須保留原文並標記「不可解讀」，不得丟棄（前向相容）。

## 四、概念：開放詞彙的落地（憲法附錄 #3）

`raw_text` 永遠保存 Provider 的原話（"rusty bolt"）；`taxonomy_node_id` 是映射到本專案 Taxonomy 概念卡的結果（可為空＝尚未映射）；`mapping_provenance` 記錄這個映射是誰做的（人／規則／某 LLM 的哪一版）——**映射本身也是有出處的意見**，因為「rusty bolt 算不算本專案的『鏽蝕』」正是語彙漂移的高發地。

## 五、信心：原始與校準分離（憲法 §3 Confidence）

`raw` 為 Provider 自報原值（僅同 Provider 同版本內可比）；`calibrated` 為經 Golden Dataset 校準後的實測精確率映射（可空）；`calibration_ref` 指向校準曲線版本；`reliability ∈ {none, low, high}` 由校準樣本量決定（R2 9.2 的收縮估計）。**分流邏輯只准讀 calibrated；reliability=none/low 時憲法規定一律人審。** Schema 把這條憲法直接寫進欄位語意。

## 六、生命週期與 Label 的誕生（D7）

```
draft ──路由──▶ queued(fast|detail|manual) ──人審──▶ approved / edited_approved / rejected
```

`approved`／`edited_approved` 時生成**不可變的 Label 記錄**（引用 claim_id、保存最終幾何與概念、審核者與時間、edit_delta 保留人改了什麼——這是血統與盲審比對的原料）。Label 是新記錄而非 Claim 的狀態變更，理由：Claim 帳本永遠保持 Provider 原始輸出，人修過的痕跡分離存放，兩者對照才能量測 Provider 真實錯誤率（防線五的資料基礎）。

## 七、刻意不放進 Schema 的東西

業務欄位（讀值、計數——那是 Application Pipeline 的事，F8 另立輸出契約）、UI 狀態（選取、高亮）、成本明細（帳本持有，這裡只留 ref）、Provider 私有雜項（收進 `provider_extra` 不透明袋，核心不解讀、原樣保存）。

## 八、開放問題（請討論後定案）

1. **mask 儲存格式**：RLE（COCO 慣例、省空間）vs PNG（人類可直接看）？傾向 RLE＋縮圖快取。
2. **否定陳述（negative claim）**：「此圖確認無任何目標」要不要一等公民？傾向要——Golden Dataset 需要「已驗證的空圖」，且 R1 健檢 #11（負樣本）依賴它。
3. **keypoints 的骨架定義**歸屬：任務模組擁有（傾向）vs Schema 內嵌。
4. **provider_extra 的大小上限**：不設限會被濫用成垃圾場，設多少？
5. **claim 與影片**（F2）：v0.1 是否直接預留 `temporal_span` 欄位，或等 M2？傾向只在信封留 media type 擴充點，欄位不預建（A10）。

## 九、憲法對照

| 條文 | 本設計的回應 |
|---|---|
| PR2（唯一耦合點、N/N-1） | schema_version 欄位＋只增不改的型別策略 |
| PR6（版本即身分） | producer 三元組＋prompt_ref 必填 |
| F1/F2（幾何/模態可擴充） | 型別化聯集＋未知型別保留策略 |
| D3（可重放） | run 連 decision_ref、claims 保存原始輸出 |
| D7（Claim 不成 Label） | Label 為獨立不可變記錄，唯一入口是 review 狀態機 |
| A5（確定性內核） | Schema 由 Pydantic 驗證，非法資料在邊界被拒 |
| A10（Rule of Two） | 五個幾何型別都有現實消費者；temporal_span 不預建 |
