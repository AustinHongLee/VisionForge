# app

本機 FastAPI 服務、圖片匯入／查詢、Teacher 接線、Dataset freeze、child-process Trainer、Evaluation、Apply 與 CapabilityRelease builder。

它可以依賴 `visionforge_core` 與 `visionforge_providers`；core 不得反向依賴 app。Trainer 失敗、取消或中斷不註冊 Artifact；Release builder 只封裝已有 EvaluationReport 的不可變 Artifact。

本地訓練依賴安裝：

```powershell
.\.venv\Scripts\python -m pip install -e "app[training]"
```
