# VisionForge Execution

| 項目 | 現況 |
|---|---|
| 基準 | VisionForge 重構開工書 R3 |
| 分支 | `codex/visionforge-first-forge` |
| 實作範圍 | Slice 0～4 |
| 程式狀態 | First Forge 垂直路徑已接通 |
| 品質裁定 | 自動化與可攜 runner parity 已證明；真實領域準確度與最終人類桌面走查尚未宣稱完成 |

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
