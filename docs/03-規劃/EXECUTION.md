# VisionForge Execution

| 項目 | 現況 |
|---|---|
| 基準 | VisionForge 重構開工書 R3 |
| 分支 | `codex/visionforge-first-forge` |
| 實作範圍 | Slice 0～4 |
| 程式狀態 | First Forge 垂直路徑已接通 |
| 品質裁定 | 自動化與可攜 runner parity 已證明；真實領域準確度與最終人類桌面走查尚未宣稱完成 |

## 跨電腦接續

目前可接續基線位於遠端分支 `codex/visionforge-first-forge`。在 Draft PR 合併前，另一台電腦直接 clone 此分支即可，不必重播聊天紀錄：

```powershell
git clone --branch codex/visionforge-first-forge --single-branch https://github.com/AustinHongLee/VisionForge.git
cd VisionForge
git status --short --branch
```

應看到乾淨工作樹，且 HEAD 至少包含以下垂直提交：

| Commit | 交付內容 |
|---|---|
| `7e9a4b5` | 建立 R3 誠實基線 |
| `c1f59af` | 修正持久化、身分與原子性 |
| `b84b048` | 第一條持久化教學迴圈 |
| `86b6464` | Dataset、訓練、Evaluation 與 Apply |
| `80673e2` | 可攜 CapabilityRelease 與 v1／v2 證據 |
| `8b13ddb` | Project、雲端同意、鍵盤操作、文件與完整 First Forge 收尾 |

新電腦第一次啟動：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e core -e providers -e "app[training]" pytest ruff
pnpm --dir ui install
.\start-visionforge.bat --check
.\start-visionforge.bat
```

若電腦沒有全域 Node／pnpm，Codex Desktop 的 bundled runtime 可供 `start-visionforge.bat` 使用。不要複製 `.venv`、`node_modules`、Project 資料夾或 API key；它們都不是 repo 接續條件。

## 本輪討論留下的產品判決

這些是後續 Agent 不應從頭重辯的框架；只有真實使用證據推翻時才修改：

1. VisionForge 是通用的「視覺能力鑄造工具」，不是只服務工程圖，也不是 YOLO GUI。通用的是教學、版本、訓練、驗證與交付流程。
2. 大型通用模型是 Teacher：先提出可錯的草稿；人類修正後的資料才是訓練真相；本地 Student／CapabilityRelease 才是可被使用者帶走的成果。
3. 使用者是 Direction Setter，不是 Schema、ADR、PR 或模型分工的技術審核者。Agent 應自行完成可逆技術決策，只把真正不可逆的產品方向交回使用者。
4. Studio 負責 import／teach／train／evaluate／release。第一個 Release 只附最小 runner；第二個真實消費者出現前，不抽通用 Runtime、DAG 或 Plugin 平台。
5. A 切到 B 必須有穩定 Concept identity、DatasetVersion 與每張圖每個 Concept 的 Coverage。未檢查是 `unverified`，永遠不是 negative。
6. 單一 detect Task 可先使用多類別模型；不預設每個物件一個模型。只有輸出形狀、部署或責任真的不同時才拆 Task／Artifact。
7. 工程圖是未來的 Domain Pack 壓力測試。Layout、OCR、BOM、pipe、symbol、relation 與規則很可能需要多模型，但不得提前硬編碼進通用 Core。
8. 預設 Trainer 暫用自有 PyTorch tiny detector、零預訓練權重，目的是證明完整產品旅程，不宣稱專業品質。替換 Trainer 時仍須保持 Dataset／Artifact／Release 契約與授權清楚。
9. 歷史治理文件與舊票保留供考古；當它們與 R3、程式和端到端行為衝突時，現行程式證據與 R3 優先。

## 給下一位 Agent 的直接開工提示

```text
你正在接續 VisionForge，遠端基線是 codex/visionforge-first-forge。

先讀：
1. README.md
2. docs/03-規劃/VisionForge_重構開工書_R3.md
3. docs/03-規劃/EXECUTION.md
4. 當期相關程式與 git log；舊憲法、票務、Architect 手冊只在考古時讀。

目前 Slice 0～4 已接通並有自動化證據。不要重做治理，不要先建 Runtime／DAG，
也不要把 unverified 當 negative。使用者是 Direction Setter，不要求他技術審核。

第一優先：用真實 A／B 圖片與真 OpenAI 設定走一次 Windows 桌面驗收，記錄實際卡點。
若旅程成立，再依證據二選一：
- 換入授權清楚、品質更高的 provisional Trainer Adapter；或
- 以單一公司／單一圖面家族啟動 Engineering Drawing Pack Slice 5。

任何修改都要保住 DatasetVersion、ModelArtifact、CapabilityRelease 的不可變性，
以及 Project／Provider version 級雲端同意。完成後跑 README 的全套驗證與 Electron smoke。
```

## Slice 真相

| Slice | 已落地證據 | 尚未冒充完成的部分 |
|---|---|---|
| 0 可信基線 | run-scoped Claim ID、跨 repository transaction、server-owned reference、終局審核唯一性、schema v3 additive migration、正式模式不靜默 fallback | Legacy API 暫留相容，不再是主 UI |
| 1 教 A | Project 建立／開啟／記憶、Task／Concept／Coverage、持久 Teacher 建議、可編輯 revision 畫布、鍵盤操作、雲端 per-project consent | 尚未對真 OpenAI 帳號做本次分支的人工桌面走查 |
| 2 鑄造 A | Task-scoped immutable DatasetVersion、readiness、source-group split、child-process TrainingRun、取消／中斷、ModelArtifact、Evaluation、Apply、feedback | Provisional tiny detector 不代表專業資料品質；沒有 GPU／雲端訓練 |
| 3 帶走 A | 單 Artifact CapabilityRelease、manifest、runner、requirements lock、I/O Schema、license inventory、parity fixture | 沒有獨立 Runtime 產品或 Studio installer |
| 4 加入 B | 測試證明 B 對舊圖起始為 `unverified`；v2 建立後 v1 Dataset／Release record／ZIP hash 不變 | UI 目前逐張重掃舊圖，尚無智慧排序或大量批次操作 |

## 機械驗證

全套守門：

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check core app providers
pnpm --dir ui test -- --run
pnpm --dir ui build
```

高風險路徑另有測試守住：

- schema v3 → 現行 schema 的 additive migration，舊資料不重寫。
- `unverified` 不進 negative；同 content hash／source group 不跨 split。
- validation feedback 進下一版 train 後，不能繼續留在 validation。
- 真 CPU train → `.pt` → reload → infer。
- Release ZIP 實際解壓後，在 Studio 外執行 runner 並取得 parity JSON，且不需要 `project.db`。
- Release 鎖定依賴已在全新 Windows venv 從公開 PyPI＋PyTorch CPU index 安裝，`--verify-parity` 通過。
- 加 B 並發布 v2 後，v1 Dataset、Release record 與 archive hash 保持不變。

## 授權路徑

預設 Trainer 使用 PyTorch、自有 tiny detector 程式與零預訓練權重；Release 內附第三方清單。Ultralytics 沒有成為預設依賴，避免在產品與再散布條件未另行裁決前，把 AGPL／Enterprise 選擇帶進主線。

## 下一條合理施工線

先用一組真實但容易取得的 A／B 圖片做人類桌面走查，記錄哪個 UX 或 readiness 規則真的卡人；再決定要優先換成品質更高且授權清楚的 Trainer Adapter，或開始單一圖面家族的 Engineering Drawing Pack。這兩者都不需要先建立通用 DAG。
