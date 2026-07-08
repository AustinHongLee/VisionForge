# 票-0010：Electron 起 FastAPI sidecar（UI↔Python 橋的 Electron 側）

| 項目 | 內容 |
|---|---|
| 狀態 | 🟨 已發出（2026-07-08） |
| 承包 | Codex（Builder） |
| 審查層級 | **L2 必審**（觸及 `ui/src/main`／`preload`／CSP＝票-0002 安全殼；**Architect 合併前審查**，協議 §3-2） |
| 政策依據 | ADR-0009（Electron 管本機 FastAPI sidecar）；消費票-0009 的 `python -m visionforge_app.api` 入口 |

## 【目標】

Electron 主行程在 app 啟動時 spawn 票-0009 的 FastAPI sidecar（綁 `127.0.0.1`）、輪詢 `/health` 就緒後才載入視窗、app 結束時終止子行程；renderer 經 Bridge 取得 API base URL。**維持票-0002 安全殼：僅以白名單放行 loopback，其餘防護（導航鎖、openExternal 白名單、其他 CSP 指令）不得回退。**

## 【範圍】（白名單）

`ui/**`。可改 `ui/src/main/**`（sidecar 生命週期、埠選擇）、`ui/src/preload/**`＋`ui/src/shared/{bridge,ipcChannels}.ts`（新增 base URL 通道）、`ui/src/renderer/index.html` 的 **CSP `connect-src`**（僅新增 `http://127.0.0.1:*`）、對應測試。

**不得動**：`app/**`、`core/**`、`providers/**`、`.github/**`、`scripts/**`、根/子 `pyproject.toml`。

## 【介面】（已凍結——簽名與行為照此）

1. **Bridge 新增一支**（`ui/src/shared/bridge.ts` 的 `DesktopBridge`）：
   ```ts
   getApiBaseUrl(): Promise<string>;   // 回 "http://127.0.0.1:{port}"（就緒後）
   ```
   搭配 `ipcChannels.ts` 新增一個 channel（沿票-0001/0002 既有模式）。
2. **主行程生命週期**：
   - app `ready` → 選一個**空閒 loopback 埠** → spawn Python sidecar，傳 `VISIONFORGE_API_PORT={port}`、`VISIONFORGE_PROJECT={dev 專案路徑}`（dev 假設 python 在 PATH＋工作區已安裝；spawn 指令可經 env `VISIONFORGE_PYTHON` 覆寫，預設 `"python"`）。
   - 輪詢 `GET /health` 直到 `{"status":"ok"}` 或逾時（逾時 → 顯示明確錯誤，不靜默白畫面）。
   - 就緒後才 `loadURL`/`loadFile`。
   - app `will-quit`/`window-all-closed` → 終止子行程（不留孤兒）。
3. **CSP**：`connect-src` 追加 `http://127.0.0.1:*`（loopback 任意埠）。**其餘 CSP 指令、導航鎖、openExternal 白名單原封不動**（票-0002）。

## 【工作項】

1. 埠選擇工具（取空閒埠）＋ sidecar spawn（`child_process`）＋ 環境傳遞。
2. `/health` 輪詢（含逾時與失敗處理）。
3. 生命週期綁定（就緒才開窗；退出終止子行程；single-instance 下不重複 spawn）。
4. Bridge `getApiBaseUrl` 的 main handler＋preload 暴露＋型別。
5. CSP `connect-src` 加 `http://127.0.0.1:*`。

## 【驗收】（測試清單＝完成的唯一定義）

1. 單元（vitest，子行程/ fetch 以 mock）：埠選擇回合法埠；`getApiBaseUrl` 回 `http://127.0.0.1:{port}`；health 輪詢在 mock ok 後 resolve、逾時走錯誤路徑。
2. **票-0002 安全回歸不破**：既有 `urlPolicy` 測試維持綠；CSP 僅新增 `connect-src` 的 `127.0.0.1:*`，其他指令 diff 為零（測試或快照佐證）。
3. 依賴紀律：renderer 仍無 `import electron`；`depcruise` 綠。
4. `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm depcruise`、`pnpm build` 全綠。
5. （手動/整合，不入 CI）dev 啟動：sidecar 起、`/health` 通、視窗載入；關閉 app 後無殘留 python 行程。

## 【憲法】

ADR-0009（sidecar 生命週期、localhost 離線）、票-0002 安全殼不回退（僅白名單放行 loopback）、A3/D13（renderer 經 Bridge，不直連 electron/後端）、§7.3（只連 loopback）、D14（sidecar 起不來要有明確錯誤，不白畫面）。

## 【禁區】

不得放寬 CSP 除 `connect-src` 的 `127.0.0.1:*` 以外任何項；不得動導航鎖／openExternal 白名單；不得綁或連非 loopback；不得 renderer 直 `import electron`；不得動 `app/**`、`core/**`、`.github/**`、`scripts/**`、`pyproject.toml`；規格衝突或缺件 → 停手回報，不腦補。

## 【交付物】

PR 一個（分支建議 `codex/ticket-0010-electron-sidecar`），說明含 D20 憲法聲明＋驗收勾選。**L2 票：CI 綠後仍需 Architect 合併前審查**（聚焦 CSP diff 僅 loopback、票-0002 防護未回退、子行程生命週期無孤兒）。pr-scope 會標 L2。
