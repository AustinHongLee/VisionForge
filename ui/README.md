# ui/ — Electron + React + TypeScript 殼（Codex 地盤，票-0001）

規則：Renderer 一律經 Bridge 介面使用桌面能力，**禁止直接 import electron**（A3，dependency-cruiser 強制）；TS 型別未來由 core 的 JSON Schema 生成，不得手寫平行定義。

施工規格見 `docs/06-規格票/票-0001-UI殼與Bridge.md`。
