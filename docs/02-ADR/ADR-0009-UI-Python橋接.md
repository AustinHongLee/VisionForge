# ADR-0009：Electron 管理本機 FastAPI sidecar 作為 UI↔Python 執行時橋接

| 項目 | 內容 |
|---|---|
| 編號 | ADR-0009 |
| 日期 | 2026-07-08 |
| 狀態 | 🟨 提案（合併含本 ADR 的 commit 即視同採納；有異議回報即改） |
| 決策者 | 李宗鴻（Claude 起草） |

## 背景

前端是 Electron（Node/TS），核心與服務是 Python（確定性保留區在 Python，憲法 A5）。ADR-0002 已選 FastAPI 作後端框架。要讓「看懂」站顯示真實 `Claim`，renderer 必須能呼叫 Python 的匯入／列表／推論。缺的是「怎麼接」的具體執行時決策。R2 §9.5 警告「把 GB 級 Python runtime 打包進安裝檔」是被名字掩蓋的硬問題；§7.3 要求離線是桌面工具的本分。不決策，UI 就永遠只能吃 stub。

## 決策

**Electron 主行程管理一個本機 FastAPI sidecar；renderer 經 localhost HTTP 呼叫它。**

1. **Python 側**：一個 FastAPI 服務綁 `127.0.0.1`（固定或協商埠），暴露 M0 端點：`POST /import`、`GET /media`（分頁）、`GET /media/{hash}/thumbnail`、`POST /infer`（影像＋concepts → Claims，先用已合併的 fixture provider）、`GET /health`。
2. **Electron 主行程**掌生命週期：app 啟動時 spawn sidecar → 輪詢 `/health` 就緒 → 視窗載入；關閉時終止子行程。renderer 一律經既有 Bridge/IPC 或直接 `fetch` localhost API。
3. **離線優先**：服務只綁 loopback、不對外；除非使用者主動選用雲端 provider，否則零外網（§7.3／§9.5）。票-0002 安全殼**不回退**——CSP 以白名單允許 `127.0.0.1` 既定埠，導航鎖與 openExternal 白名單維持。
4. **打包延後**：dev 從 venv 跑 sidecar；把 Python runtime 嵌入安裝檔（PyInstaller／embeddable）是 **M1 的獨立硬問題**，本 ADR 不解，只保證介面穩定讓打包可後補。
5. **契約邊界**：API 請求/回應型別**沿用既有契約的 JSON Schema/TS 生成物**（票-0004 管線）——前端拿到的就是 `MediaRecord`／`Claim` 型別，不另手寫平行定義。

## 理由

- 承接 ADR-0002（FastAPI），不另立門派；持久服務比「每次操作 spawn 一次性 CLI」更適合多操作、有狀態的桌面 app。
- 把「打包 Python runtime」這個硬問題**隔離並延後**，不讓它阻塞可見進度——dev 先跑通、看到框，打包留給 M1。
- localhost-only 落實離線本分（§7.3）；型別重用讓前後端契約不漂移（票-0004 守門延伸到 API）。

## 曾考慮的替代方案

- **每操作 spawn 一次性 Python CLI** → 棄（多操作/狀態/效能差；僅可作極早期 fallback）。
- **Pyodide/WASM 把核心塞進 renderer** → 棄（Pillow／未來 torch 等原生相依不可行）。
- **用 Node 重寫核心** → 棄（違反「確定性保留區在 Python」，A5/D11；且拋棄既有 kernel）。
- **Electron 直接以 stdio 長駐子行程協定** → 暫棄（可行但要自造協定；FastAPI 的 HTTP＋OpenAPI 更標準、可測、與型別管線契合）。

## 影響範圍

- **新增**：service 層（FastAPI app，消費 core/app/providers）——建議獨立套件 `service/` 或落 `app/`。
- **ui/src/main**：sidecar 生命週期管理（觸及票-0002 安全殼 → **L2 必審，Architect 審**）。
- **ui renderer**：API client ＋「看懂」站畫框 UI（L0，**Figma 設計驅動，決策者可輔助**）。
- CSP：允許 `127.0.0.1:{port}`（票-0002 範圍內微調，L2）。
- 相關 ADR：ADR-0002（技術棧）、ADR-0008（provider，infer 端點消費它）、票-0004（型別管線）。

## 憲法檢核（D19／D20）

- **觸及條文**：ADR-0002（FastAPI）、憲法 §7.3（離線本分）、R2 §9.5（打包硬問題延後）、D13（依賴方向 ui→service→core）、A5（契約型別重用、確定性核心留 Python）、票-0002 安全殼不回退。
- **合規聲明**：未修改憲法或既有凍結契約；安全殼以 localhost 白名單方式擴充而非放寬外網；打包延後不牴觸任何條文。provider 之 infer 走 ADR-0008 provisional 介面（仍不凍結）。
- **未牴觸**，無需修憲。惟若新增跨文件結構名（如 API 的 `InferResponse`）→ 依例登記 01-定義（需人）。

## 後續行動

1. 【Architect】定 API 契約（端點清單＋請求/回應型別，重用生成物）→ 可作 L2 骨架票或親手。
2. 【Architect scaffold ＋ Codex 實作】service 套件與 FastAPI 端點（消費 fixture provider 走通 `/infer`）。
3. 【Codex，L2（觸 ui/src/main＋CSP），Architect 審】Electron sidecar 生命週期＋health 就緒。
4. 【Codex，L0，**Figma 驅動**】「看懂」站：縮圖上疊出 Claim 框、接 API client——決策者可看畫面/Figma 輔助。
5. 之後 fixture → 真 provider drop-in（雲端 VLM 或本地開放詞彙，屆時再依金鑰/離線取捨發票）。
