# VisionForge 文件中心（docs/）

> 本頁是全部文件的**總索引與狀態板**。任何人——包括任何 AI Agent——進入本專案，從這一頁開始讀。

---

## 一、現行效力層級

```
1. Owner 最新明示方向
2. VisionForge 重構開工書 R3  ← 現行產品、資料語意與 Agent 施工基準
3. R3 明確保留的資料／安全原則
4. 與 R3 不衝突的已採納 ADR 與實際程式契約
5. 其餘文件                  ← 歷史證據或設計素材
```

2026-07-13 前的憲法、AI 分工協議、R1／R2、規格票與交接手冊保留供考古，但不再阻擋 R3 垂直施工。`01-定義` 在 R3 資料模型穩定前同樣視為 legacy glossary，不要求先擴寫詞典才能實作。

## 二、狀態圖例（做完 vs 沒做完，一眼判斷）

| 標記 | 狀態 | 意義 |
|---|---|---|
| 🟩 | 定案（現行） | **做完**。有約束力，可作為開發依據 |
| 🟨 | 討論中 | 沒做完。內容不穩定，不得引用為依據 |
| 🟦 | 草稿 | 沒做完。單方起草，尚未進入討論 |
| 🟧 | 部分失效 | 做完過，但部分被上位文件推翻——引用前必查失效清單 |
| ⬛ | 已歸檔 | 生命週期結束，僅供考古 |

## 三、文件登記表（新增任何文件必須在此登記）

| 文件 | 分類 | 版本 | 狀態 | 說明 |
|---|---|---|---|---|
| [VisionForge_Constitution_v1.0.md](00-法規/VisionForge_Constitution_v1.0.md) | 法規 | v1.0 | 🟧 部分失效 | R3 延續資料主權、provenance、人工權威、可回滾、可驗證與 Rule of Two；其餘產品／治理限制不再優先 |
| [VisionForge_AI分工協議_v1.md](00-法規/VisionForge_AI分工協議_v1.md) | 法規 | v1.2 | ⬛ 已歸檔 | 已由 R3 §9 的 Lead／Builder／Independent Reviewer／E2E QA 取代 |
| [交接手冊.md](交接手冊.md) | 治理 | 活文件 | ⬛ 已歸檔 | 僅保留環境與歷史線索，不再作為 Architect 接任程序 |
| [名詞定義表.md](01-定義/名詞定義表.md) | 定義 | legacy | 🟧 部分失效 | 舊語彙索引；R3 新資料模型穩定後再擷取仍有效名詞 |
| [ADR-模板.md](02-ADR/ADR-模板.md) | ADR | v1 | 🟩 定案 | 一切架構決策的固定格式 |
| [ADR-0001-文件治理結構.md](02-ADR/ADR-0001-文件治理結構.md) | ADR | — | 🟧 部分失效 | 目錄可保留；舊效力層級、修憲與票務前置已由 R3 取代 |
| [ADR-0002-技術棧選定.md](02-ADR/ADR-0002-技術棧選定.md) | ADR | — | 🟩 已採納 | Electron＋React/TS＋FastAPI＋SQLite＋CI 守門鏈 |
| [ADR-0003-Claim-Schema-v1.md](02-ADR/ADR-0003-Claim-Schema-v1.md) | ADR | — | 🟧 部分失效 | Geometry／provenance 基座保留；「Label 必須源自 Claim」已由 R3 取代 |
| [ADR-0004-帳本Schema-v1.md](02-ADR/ADR-0004-帳本Schema-v1.md) | ADR | — | 🟧 部分失效 | 歷史帳本相容性保留；Decision／Cost／Golden 不再強制位於 First Forge 主線 |
| [ADR-0005-儲存層設計.md](02-ADR/ADR-0005-儲存層設計.md) | ADR | — | 🟩 已採納 | 文件式 SQLite＋append-only repos＋遷移＋blob 庫；含本 ADR 之 commit 已合併（661f5c1），視同採納 |
| [ADR-0006-匯入正規化與媒體身分政策.md](02-ADR/ADR-0006-匯入正規化與媒體身分政策.md) | ADR | — | 🟩 已採納 | 媒體身分＝入庫位元組雜湊；EXIF 轉正 Policy B；Pillow 釘版；縮圖規格；隨票-0003 合併（4ab83f7），視同採納 |
| [ADR-0007-校準引擎.md](02-ADR/ADR-0007-校準引擎.md) | ADR | — | ⬛ 已歸檔 | 實作保留供研究；現有血統與統計語意不足，不再作為 First Forge 主線或品質宣稱 |
| [ADR-0008-VisionProvider抽象.md](02-ADR/ADR-0008-VisionProvider抽象.md) | ADR | — | 🟧 部分失效 | Teacher 接入經驗保留；R3 改採 TeacherAdapter／TrainerAdapter／ModelRunner 三個窄介面 |
| [ADR-0009-UI-Python橋接.md](02-ADR/ADR-0009-UI-Python橋接.md) | ADR | — | 🟩 已採納 | Electron 管理本機 FastAPI sidecar；localhost 離線優先；打包延後 M1；API 型別重用契約生成物；採納 a0d4bcb，票-0009/0010/0011 已落地（M0 端到端達成） |
| [ADR-0010-審核中心骨架.md](02-ADR/ADR-0010-審核中心骨架.md) | ADR | — | ⬛ 已歸檔 | 舊 Claim 審核／Golden／校準閉合方案；由 R3 教學工作區、Coverage 與 Label revision 模型取代 |
| [20260707-claim-schema-草案.md](05-討論/20260707-claim-schema-草案.md) | 討論 | v0.1 | ⬛ 已歸檔 | 已落地於 ADR-0003＋契約程式碼 |
| [票-0001-UI殼與Bridge.md](06-規格票/票-0001-UI殼與Bridge.md) | 規格票 | — | ⬛ 已結案 | 審查通過（Blocking 0）；Non-blocking 5 項移票-0002 |
| [票-0002-UI殼安全加固.md](06-規格票/票-0002-UI殼安全加固.md) | 規格票 | — | ⬛ 已結案 | L0 合併＋L1 抽查通過；openExternal 白名單、導航鎖、CSP、depcruise 擴充 |
| [票-0003-匯入管線.md](06-規格票/票-0003-匯入管線.md) | 規格票 | — | ⬛ 已結案 | L0 免審合併（4ab83f7）；pytest 66 綠、ruff/D1·D13 守門通過、凍結介面守門測試綠 |
| [票-0004-Schema匯出與TS-codegen.md](06-規格票/票-0004-Schema匯出與TS-codegen.md) | 規格票 | — | ⬛ 已結案 | L2 審查通過（Blocking 0）合併（7ef91be）；契約 JSON Schema 匯出＋TS codegen＋雙向漂移守門 |
| [票-0005-app匯入與查詢服務.md](06-規格票/票-0005-app匯入與查詢服務.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（728f03d）；import_directory 批次匯入；media 查詢服務待 core 補列舉方法後另票 |
| [票-0006-ui殼導航與匯入頁.md](06-規格票/票-0006-ui殼導航與匯入頁.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（f360caf）；L1 抽審通過（0 問題）；導航「看懂/整理/鑄造/應用」＋匯入頁；型別取自 contracts.generated |
| [票-0007-app-media查詢服務.md](06-規格票/票-0007-app-media查詢服務.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（4cc57d3）；list_media 分頁＋get_media＋thumbnail_path |
| [票-0008-fixture-provider.md](06-規格票/票-0008-fixture-provider.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（11ca65f，PR #8）；第一個 provider（確定性 fixture）走通 provider→Claim→校準 |
| [票-0009-FastAPI服務層.md](06-規格票/票-0009-FastAPI服務層.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（ca822ff，PR #9）；本機 FastAPI（/health /media /thumbnail /import /infer）；116 測試綠 |
| [票-0010-Electron-sidecar.md](06-規格票/票-0010-Electron-sidecar.md) | 規格票 | — | ⬛ 已結案 | L2 審查通過（Blocking 0）合併（bb835bf，PR #10）；Electron 起 sidecar＋health＋CSP 放行 127.0.0.1；CSP 快照測試護欄 |
| [票-0011-看懂站畫框UI.md](06-規格票/票-0011-看懂站畫框UI.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（0e96871，PR #12，19 測試）；「看懂」站接後端、匯入→縮圖→偵測→**畫框**＋信賴度三色。**M0 第一個端到端達成** |
| [票-0012-app-process-media.md](06-規格票/票-0012-app-process-media.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（e26eec3，PR #16，app 45 測試）；process_media 跑 provider→orchestrator 入帳存 run＋POST /process |
| [票-0013-app審核API.md](06-規格票/票-0013-app審核API.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（d803c55，PR #18，app 51 測試）；審核 API（pending/approve/reject/golden）接 core 狀態機 |
| [票-0014-app校準接線.md](06-規格票/票-0014-app校準接線.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（68edb82，PR #20，app 54 測試）；process_media/infer 回填信賴度＋POST /recalibrate |
| [票-0015-整理站審核UI.md](06-規格票/票-0015-整理站審核UI.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（0183702，PR #21，ui 25 測試）；「整理」站審核 UI。**M0 資料飛輪完整閉合** |
| [票-0016-app資料集匯出.md](06-規格票/票-0016-app資料集匯出.md) | 規格票 | — | ⬛ 已結案 | L0 CI 綠自併（de219fb，PR #23，app 59 測試）；POST /export 版本快照＋YOLO/COCO。**M0 資料工房完整可出貨** |
| [票-0017-OpenAI-provider.md](06-規格票/票-0017-OpenAI-provider.md) | 規格票 | — | ⬛ 已結案 | L2 re-review 通過合併（2f52b2e，PR #24）；第一個真實老師（OpenAI 雲端 VLM）＋sidecar 防孤兒＋provider 錯誤回 CORS 502＋base_url 釘版。**實機對 cat 圖畫框成功** |
| [VisionForge_重構開工書_R3.md](03-規劃/VisionForge_重構開工書_R3.md) | 規劃 | R3 | 🟩 定案 | **現行產品重構與 Agent 施工基準**；legacy 文件整理與產品施工可平行 |
| [EXECUTION.md](03-規劃/EXECUTION.md) | 執行 | 活文件 | 🟩 現行 | Slice 0～4 實作真相、跨電腦接續、產品判決、機械驗證、限制與下一條施工線 |
| [GoodYolo_產品規劃書.md](03-規劃/GoodYolo_產品規劃書.md) | 規劃 | R1 | ⬛ 已歸檔 | 已由 VisionForge 重構開工書 R3 取代，僅供考古 |
| [GoodYolo_架構評審_R2.md](04-評審/GoodYolo_架構評審_R2.md) | 評審 | R2 | ⬛ 已歸檔 | 已完成歷史使命；未被 R3 重申的結論不得作為現行施工依據 |

## 四、目錄規則（未來大量 md 的家）

| 資料夾 | 住什麼 | 命名規則 |
|---|---|---|
| `00-法規/` | 2026-07-13 前的憲法、協議歷史原文 | 保留原名與頂部狀態標記，不再新增企業式法規 |
| `01-定義/` | 名詞定義表（單一檔案，活文件） | 固定 |
| `02-ADR/` | 架構決策紀錄 | `ADR-NNNN-標題.md`，編號遞增不重用 |
| `03-規劃/` | 產品規劃（R1、未來 R3…） | 沿用既有名或 `R{n}_主題.md` |
| `04-評審/` | 評審與挑戰報告 | 同上 |
| `05-討論/` | **一切未定案的思考**（規則見該夾 README） | `YYYYMMDD-主題.md` |
| `06-規格票/` | 歷史施工票，保留 commit 與決策線索；不再新增 | 保留原名 |

**現行生命週期**：討論素材收斂進 R3、Architecture、Execution 或真正必要的 ADR；歷史檔保留但不再以修憲／票務程序作為一般產品施工前置。

**三條文件習慣**：
1. 新文件 → 登記於本頁「文件登記表」。
2. 新資料模型術語先在 R3／現行 Architecture 定義；穩定後再同步 glossary，避免為字典阻擋實驗。
3. 狀態變更（定案、失效、歸檔）→ 同步更新檔內狀態列與本頁登記表。

## 五、AI Agent 守則

1. 進場先讀 R3、README 與當期相關程式；只在需要歷史理由時讀 legacy docs。
2. 程式、資料與真實端到端行為優先於舊票面完成狀態。
3. 一位 Lead 對垂直成果負責；Builders 可跨目錄，高風險變更才需要獨立 Reviewer。
4. 使用者是 Direction Setter，不負責逐項技術審核；只有真正的產品方向或不可替代的外部選擇才交還使用者。
5. 不要求每個 commit 引用憲法條文，也不以文件數、票數或審查計數代替可運作的使用者旅程。
