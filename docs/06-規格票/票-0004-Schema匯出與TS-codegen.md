# 票-0004：契約 JSON Schema 匯出與 TS 型別生成

| 項目 | 內容 |
|---|---|
| 狀態 | 🟦 草稿（2026-07-08，待決策者發包給 Codex） |
| 承包 | Codex（Builder） |
| 審查層級 | **L2 必審**（觸及 `scripts/`、`.github/`，建立契約→TS 消費路徑；Architect 合併前審查，協議 §3-2） |
| 政策依據 | ADR-0002（技術棧：唯一事實來源＝core Pydantic 契約）、ADR-0003（Claim Schema 唯一事實來源＝`contracts/claims.py`） |

## 【目標】

把 core 的 Pydantic 契約**自動匯出**成單一 JSON Schema 快照（機器可讀），再由該 JSON Schema **生成** UI 端 TypeScript 型別；CI 雙向守門——Pydantic 改了沒重匯出、或 schema 改了沒重生成 TS，即紅燈。**契約語意不變，本票只做只讀匯出與衍生生成，Pydantic 恆為唯一權威。**

## 【範圍】（白名單）

- `scripts/**`：新增 `scripts/export_contract_schema.py`。
- `schema/**`（新目錄）：入庫產物 `schema/contracts/visionforge-contracts.schema.json`。
- `ui/**`：新增 devDep `json-schema-to-typescript`（釘版）、`package.json` script、入庫生成物 `ui/src/shared/contracts.generated.ts`、至少一處消費示範。
- `.github/workflows/ci.yml`：core job 與 ui job 各加一漂移守門步驟。
- 文件：`ui/README.md` 或根 `README.md` 記一行生成流程。

## 【介面】（已凍結——匯出機制規格，不得偏離）

1. **匯出來源**＝`visionforge_core.contracts.__all__` 中所有 `pydantic.BaseModel` 子類，**程式化過濾**（`inspect` + `issubclass`），不得手列清單。非模型名稱（`SCHEMA_VERSION`、`REASON_CODES`、`MediaFormat` 等 Literal/常數）自動略過；Enum 會內嵌於引用處。
   - 當前預期 root 模型集合（**資訊性**，實際以程式過濾結果為準）：`Assertion`… 之外的 BaseModel——`BBox, Claim, Concept, ConceptMappingProvenance, Confidence, InferenceRun, Keypoints, Label, MaskRef, MediaSubject, Point, Polygon, Producer, Review, UnknownGeometry, WholeImage, CandidateProvider, CostEntry, CostMeasurement, DatasetVersionManifest, DecisionRecord, GoldenSetEntry, InputRef, ManifestEntry, PolicyRef, ProvenanceSummary, ReviewEvent, MediaRecord, MediaSource`。
2. **匯出 API**：`pydantic.json_schema.models_json_schema(models, ref_template="#/$defs/{model}")`，產生**單一 bundled 文件**，全部模型置於 `$defs`。
3. **輸出檔**：`schema/contracts/visionforge-contracts.schema.json`，寫入方式固定為
   `json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n"`（UTF-8）——確保 diff 穩定、可 `git diff --exit-code`。
4. 頂層附 `"$schema"`、`"title": "VisionForge Contracts"`、`"x-schema-version"` ＝ 契約 `SCHEMA_VERSION`（目前 `"1.0"`）。
5. **TS 生成**：`json-schema-to-typescript` 讀該 JSON Schema → `ui/src/shared/contracts.generated.ts`；檔頭含「AUTO-GENERATED — 由 schema 生成，請勿手改」；npm script 名 `gen:contracts`。
6. 匯出腳本須**確定性**：禁止時間戳、隨機、絕對路徑、環境相依輸出。提供 `--check` 模式（重新產生後與磁碟現檔比對，不同 → 印 diff、exit 1）。

## 【工作項】

1. `scripts/export_contract_schema.py`：import `visionforge_core.contracts`、程式化過濾 BaseModel 子類、`models_json_schema` 依上規格寫檔；含 `--check`。
2. 產生並入庫 `schema/contracts/visionforge-contracts.schema.json`。
3. `ui`：加 devDep `json-schema-to-typescript`（釘版）；`package.json` 加 `gen:contracts` 與 `check:contracts`（重生後對 `contracts.generated.ts` 做 `git diff --exit-code`）；產生並入庫 `ui/src/shared/contracts.generated.ts`。
4. `.github/workflows/ci.yml`：core job 末加 `uv run python scripts/export_contract_schema.py --check`；ui job 末加 `pnpm run check:contracts`。
5. **消費示範**：至少一處 `ui/src/shared` 型別改由 generated 匯入（例如把 `Reliability`／`ReviewStatus` 之類供 renderer 使用），不破壞既有 bridge 型別。
6. 文件記一行：改契約後須 `export_contract_schema.py` + `gen:contracts` 重生，兩產物入庫。

## 【驗收】（測試清單＝完成的唯一定義）

1. `python scripts/export_contract_schema.py` 產出檔存在、為合法 JSON、`$defs` 含全部公開 BaseModel（數量＝過濾集大小）。
2. 連跑兩次匯出，`git diff --exit-code schema/` ＝ 0（確定性）。
3. `pnpm run gen:contracts` 產出 TS，`pnpm run typecheck`（含 build）綠。
4. 連跑兩次 codegen，`git diff --exit-code ui/src/shared/contracts.generated.ts` ＝ 0。
5. `--check` 負向驗證（**手動、不入庫**）：本地暫改任一 Pydantic 欄位 → `--check` 紅並印 diff；還原後綠。
6. CI 新步驟在 PR 綠（core `--check`、ui `check:contracts` 皆過）。
7. **`core/**` 契約檔（claims/ledgers/media.py）零 diff**——僅被 import 讀取。
8. 既有 core／app／ui 全測試維持綠。

## 【憲法】

ADR-0002（唯一事實來源＝Pydantic 契約，TS 為衍生消費方）、ADR-0003（Claim Schema 唯一事實來源＝`claims.py`；本票產物僅為只讀快照，不得升格為第二事實來源）、PR2（`schema_version` 隨附匯出）、D1/D13（依賴方向：ui 消費 schema 檔，**不得**反向 import core）、A5（確定性產物）、A10（不預建多版本或未使用的 codegen 目標）。

## 【禁區】

- 不得修改 `core/**` 任何契約語意／簽名／欄位（只准 import 讀取；需改契約 → 走 ADR／修法，非本票）。
- 不得手改生成物 `contracts.generated.ts` 或 `visionforge-contracts.schema.json`（手改＝繞過唯一事實來源，等同紅線 6 造假）。
- 不得讓 JSON Schema 成為與 Pydantic 並存的第二權威——它是衍生快照，Pydantic 恆為主。
- 不得引入 Pydantic／`json-schema-to-typescript` 以外的 schema／codegen 工具鏈（A10）。
- 不得動 `docs/00-法規`、`docs/01-定義`；規格衝突、缺件或介面不清 → 停手回報，不腦補。

## 【交付物】

PR 一個（分支建議 `codex/ticket-0004-schema-codegen`），說明含 D20 憲法聲明＋驗收勾選。**L2 票：CI 綠後仍需 Architect 合併前審查**（聚焦：`core/**` 零 diff、匯出／生成確定性、兩產物與來源一致、CI 雙向守門到位）。
