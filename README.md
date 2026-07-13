# VisionForge

> 把大型通用模型的理解草稿，鑄造成使用者自己可驗證、可攜的專用視覺能力。

VisionForge 目前完成 First Forge 的 detect 垂直路徑：建立／開啟 Project、教 A、修正框與 Coverage、凍結 DatasetVersion、在 child process 訓練本地學生模型、查看 validation 證據、拿新圖試跑、匯出不依賴 Studio 的 CapabilityRelease，再加入 B 而不改寫 v1。

現行產品基準是 [重構開工書 R3](docs/03-規劃/VisionForge_重構開工書_R3.md)，實作與驗證真相看 [EXECUTION](docs/03-規劃/EXECUTION.md)。文件索引在 [docs/README.md](docs/README.md)。

## 現在能做

- 一個自包含資料夾代表一項視覺能力；UI 可建立、開啟並記住最近一次 Project。
- 建立 detect Task 與穩定 Concept A／B；每張圖每個 Concept 明確區分 `unverified`、`verified_complete`、`verified_absent`。
- 讓本機或雲端 Teacher 提框，再由使用者移動、縮放、刪除、補框、改類別；修訂與 tombstone 均保留。
- 雲端 Teacher 送出前顯示媒體與 Concept，並保存 Project＋Provider version 級同意；未同意時 API 也拒絕外送。
- 建立不可變 DatasetVersion，以 content hash／`source_group_id` 隔離 train 與 validation。
- 使用不含預訓練權重的本地 PyTorch provisional detector 訓練；取消、失敗、中斷不會冒充 Artifact。
- 查看 EvaluationReport、把錯誤送回教學、對未入庫圖片執行 ModelArtifact。
- 匯出含 manifest、鎖定依賴、runner、I/O Schema、license inventory 與 parity fixture 的 ZIP；runner 不讀 Project DB。
- 加入 B 時舊媒體維持 `unverified`，Dataset／Artifact／Release v1 不被覆寫，可另發 v2。

## 目前不能宣稱

- Tiny detector 是可重現的第一個 Trainer，不是通用高品質模型；實際準確度要用你的 unseen 圖片判斷。
- 不支援 PDF、影片、攝影機、BOM／OCR／管線拓撲或工程圖 Domain Pack。
- 沒有通用 DAG、獨立 Runtime、Plugin Marketplace、多人權限、雲端訓練或多 GPU。
- 本輪沒有可散布的 Studio installer；使用 repo 的 Windows dev launcher。
- 自動測試與 clean runner parity 已通過，但真實圖片／真實 OpenAI 帳號的最終產品體驗仍需人類實機走查，不能用測試數量冒充品質認證。

## Windows 開發啟動

需求：Python 3.12、Git，以及 Node／pnpm 11.7。Codex Desktop 內建 runtime 也可供 launcher 使用。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e core -e providers -e "app[training]" pytest ruff
pnpm --dir ui install
.\start-visionforge.bat --check
.\start-visionforge.bat
```

Launcher 是明示的 Developer Mode：若 repo 根目錄沒有被 Git 忽略的 `provider-config.json`，它會清楚啟用 fixture，不會把 fixture 假框偽裝成真 Teacher。OpenAI 設定格式：

```json
{
  "provider": "openai",
  "model": "gpt-5-mini",
  "openai_api_key": "replace-locally"
}
```

金鑰檔不得提交。啟動後在頁首選擇空資料夾以建立 Project，或選擇含 `project.json` 的既有 Project。

## 驗證

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check core app providers
pnpm --dir ui test -- --run
pnpm --dir ui build
```

CapabilityRelease 的 clean-environment parity 與目前已知限制記錄於 [EXECUTION](docs/03-規劃/EXECUTION.md)。
