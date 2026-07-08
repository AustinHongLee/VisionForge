# ui/ — Electron + React + TypeScript 殼（Codex 地盤，票-0001）

規則：Renderer 一律經 Bridge 介面使用桌面能力，**禁止直接 import electron**（A3，dependency-cruiser 強制）；契約 TS 型別由 core 的 JSON Schema 生成，不得手寫平行定義。

契約變更後，依序執行 `uv run python scripts/export_contract_schema.py` 與 `pnpm --dir ui run gen:contracts`，並將 JSON Schema 與 TS 生成物一併入庫。

施工規格見 `docs/06-規格票/票-0001-UI殼與Bridge.md`。
