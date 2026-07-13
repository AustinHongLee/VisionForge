# ui

Electron 主程序管理本機 FastAPI sidecar；React renderer 提供教學、鑄造、版本與應用四站。Renderer 只經 preload bridge 使用桌面能力，不直接 import Electron。

Project 切換會先啟動候選 sidecar並通過 health check，再關閉舊 sidecar；失敗時原 Project 保持可用。標註畫布支援滑鼠與鍵盤，雲端 Teacher 送出前顯示資料範圍。

契約變更後：

```powershell
.\.venv\Scripts\python scripts\export_contract_schema.py
pnpm --dir ui run gen:contracts
```

驗證：`pnpm --dir ui test -- --run` 與 `pnpm --dir ui build`。
