# 票-0001：Electron + React 殼與 Bridge 抽象層

| 項目 | 內容 |
|---|---|
| 狀態 | 🟨 已發出（2026-07-07） |
| 承包 | Codex（GPT-5.5） |
| 驗收人 | Claude 審查 → 李宗鴻合併 |

## 【目標】
建立可啟動的 Electron + React + TypeScript + Vite 應用殼：開啟一個視窗、顯示一頁 placeholder、桌面能力全部走 Bridge 抽象層。**不含任何業務功能。**

## 【範圍】（白名單，只准動這裡）
`ui/**`（保留既有 `ui/README.md`）

## 【介面】（已凍結——有異議回報，不得擅改）

Renderer 端唯一的桌面能力入口 `window.bridge`，型別如下：

```ts
// ui/src/shared/bridge.ts —— A3：前端不得直接 import electron
export interface DesktopBridge {
  pickDirectory(): Promise<string | null>;
  showNotification(title: string, body: string): void;
  openExternal(url: string): Promise<void>;
  getAppVersion(): Promise<string>;
  getPlatform(): Promise<"win32" | "darwin" | "linux">;
}
```

實作要求：main process 實作、preload 以 `contextBridge.exposeInMainWorld("bridge", …)` 注入；`nodeIntegration: false`、`contextIsolation: true`、`sandbox: true`。

## 【技術規格】
- 目錄：`ui/src/main/`（主程序）、`ui/src/preload/`、`ui/src/renderer/`（React）、`ui/src/shared/`（跨端型別）。
- 工具鏈：pnpm、Vite、TypeScript strict、electron-builder（先只配 Windows 目標）、ESLint、vitest。
- 狀態管理：暫不引入（placeholder 頁不需要）；**不得**自行引入 UI 框架大禮包（僅允許 React 本體）。
- 深色底色的空頁面，中央顯示「VisionForge — 施工中」與版本號（經 `bridge.getAppVersion()` 取得，證明 Bridge 通路活著）。

## 【驗收】（綠燈＝完成的唯一定義）
1. `pnpm install && pnpm build` 成功；`pnpm dev` 開出視窗顯示 placeholder 與版本號。
2. vitest：`DesktopBridge` 的 mock 單元測試（renderer 元件經 mock bridge 取得版本號並渲染）。
3. dependency-cruiser 規則檔就位並通過：`src/renderer/**` 與 `src/shared/**` 禁止 import `electron`。
4. ESLint 零錯誤；`tsc --noEmit` 通過。
5. 在 `.github/workflows/ci.yml` 新增 `ui` job（安裝 pnpm、build、test、depcruise）——**只准新增 job，不得改動既有 jobs**。

## 【憲法】
A3（Bridge 隔離、殼可替換）、D13（依賴方向，由 dependency-cruiser 強制）、D14 精神（之後的錯誤呈現雙層，本票先不實作）。

## 【禁區】
- 不得動 `ui/` 之外任何檔案（唯一例外：ci.yml 依驗收第 5 條新增 job）。
- 不得實作任何業務頁面、路由、狀態管理、API 呼叫。
- 不得引入票面未列的重型依賴（元件庫、CSS 框架等——之後的票再說）。
- 規格有缺陷或衝突 → 停手回報，不得腦補（分工協議 §4-5）。

## 【交付物】
PR 一個，說明需含：觸及的憲法條文聲明（D20）、驗收清單逐項勾選。
