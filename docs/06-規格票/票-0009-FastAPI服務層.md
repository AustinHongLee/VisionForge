# 票-0009：FastAPI 服務層（UI↔Python 橋的 Python 側）

| 項目 | 內容 |
|---|---|
| 狀態 | 🟨 已發出（2026-07-08，往「看懂」魔術時刻） |
| 承包 | Codex（Builder） |
| 審查層級 | **L0 免審**（app/ 白名單；FastAPI 為 ADR-0002 既定棧、ADR-0009 授權；CI 全綠＋D20 即由決策者合併） |
| 政策依據 | ADR-0009（Electron 管 FastAPI sidecar，localhost 離線優先）；消費 app 服務函式＋fixture provider（已合併） |

## 【目標】

實作本機 FastAPI 服務，暴露 M0 所需端點：健康檢查、媒體列表/縮圖、匯入、推論（infer 走已合併的 fixture provider）。這是 UI 端到端的 Python 側；Electron 之後 spawn 它（票另發）。**只綁 `127.0.0.1`、離線、消費既有凍結函式，不碰 core。**

## 【範圍】（白名單）

`app/**`。新增 `app/src/visionforge_app/api/`（FastAPI app＋路由）、於 `app/pyproject.toml` 加相依 `fastapi`、`uvicorn[standard]`、`visionforge-providers`（workspace）、`httpx`（dev/測試用 TestClient）；測試於 `app/tests/`。

**不得動**：`core/**`、`ui/**`、`.github/**`、`scripts/**`、根 `pyproject.toml`、`providers/**`、任何凍結簽名。

## 【介面】（已凍結——路由與型別照此，本體自由）

**工廠（可測，不在 import 時起服務）**：

```python
# app/src/visionforge_app/api/app.py
from fastapi import FastAPI
from visionforge_core.storage import Project

def create_app(project: Project, provider: VisionProvider | None = None) -> FastAPI: ...
# provider 預設用 visionforge_providers 的 FixtureProvider（票-0008）
```

**端點契約**（回應型別重用契約生成物，FastAPI 直接序列化 Pydantic）：

| 方法 | 路徑 | 請求 | 回應 |
|---|---|---|---|
| GET | `/health` | — | `{"status": "ok"}` |
| GET | `/media?limit=&offset=` | query | `MediaPage`（票-0007：`items: MediaRecord[]`, `total`, `limit`, `offset`, `has_more`） |
| GET | `/media/{media_hash}/thumbnail` | path | `image/jpeg` bytes；無縮圖 → 404 |
| POST | `/import` | multipart `file` | `{"media_hash": str, "deduplicated": bool, "record": MediaRecord}` |
| POST | `/infer` | JSON `{"media_hash": str, "concepts": [Concept, ...]}` | `{"claims": [Claim, ...], "provider_id": str}` |

**請求 DTO**（Pydantic，置於 api 模組，非 core 契約）：

```python
class InferRequest(BaseModel):
    media_hash: str
    concepts: list[Concept] = []   # 重用 core 的 Concept
```

**入口**（給 sidecar 用，讀環境變數開專案）：

```python
# app/src/visionforge_app/api/__main__.py 或 run()
# 讀 VISIONFORGE_PROJECT 路徑（不存在則 create_project 建），uvicorn 起 create_app 於 127.0.0.1
```

## 【工作項】

1. `create_app(project, provider)`：註冊上表路由；`provider` 預設 `FixtureProvider()`。
2. `/media`：委派 `visionforge_app.query.media.list_media`（票-0007）。
3. `/media/{hash}/thumbnail`：`thumbnail_path`（票-0007）→ 有則 `FileResponse(jpeg)`，無則 404。
4. `/import`：讀 `UploadFile` bytes → `import_media(project, data, MediaSource(kind="file", detail=filename))` → 回 `{media_hash, deduplicated, record}`；解碼失敗等 `MediaImportError` → 422，結構化訊息（不 500）。
5. `/infer`：`project.blobs.find(media_hash)` 取 bytes（無 → 404）→ `provider.infer(bytes, InferenceRequest(concepts=tuple(req.concepts)))` → 回 `{claims, provider_id}`。
6. 入口讀 `VISIONFORGE_PROJECT` 開/建專案、`uvicorn.run(app, host="127.0.0.1")`。

## 【驗收】（測試清單＝完成的唯一定義；用 `TestClient`）

1. `GET /health` → 200 `{"status":"ok"}`。
2. `POST /import` 上傳一張合法 JPG → 200，回 `media_hash`＝sha256(入庫位元組)、`record.format=="jpeg"`；`GET /media` 出現該筆、`total==1`。
3. 同圖再 `/import` → `deduplicated==true`、`total` 不增。
4. `GET /media?limit=1&offset=0` 分頁欄位正確（委派 list_media）。
5. `GET /media/{hash}/thumbnail` 存在回 200 `image/jpeg`；未知 hash → 404。
6. `POST /infer` {已匯入 hash, concepts:[{raw_text:"bolt"}]} → 200，`claims` 非空、每個 `claim.concept.raw_text=="bolt"`、`provider_id=="fixture"`；claims 為合法 Claim（Pydantic 驗證通過）。
7. `/infer` 未知 media_hash → 404；`/import` 壞位元組 → 422（非 500）。
8. `python scripts/check_forbidden_imports.py`、`ruff check app`、`pytest app/tests` 全綠。

## 【憲法】

ADR-0009（localhost 離線橋）、ADR-0002（FastAPI）、ADR-0008（infer 走 provisional 介面）、D13（依賴方向 app→core/providers，不反向）、§7.3（只綁 loopback、離線本分）、D14（錯誤結構化：422/404 非 500）、A5（回應型別重用契約，不手寫平行定義）。

## 【禁區】

不得改 `core/**`、`providers/**` 任何簽名；不得綁非 loopback 位址；不得對外連網；不得手寫與 core 契約平行的回應型別（重用 MediaRecord/Claim/Concept）；不得動 `ui/**`、`.github/**`、`scripts/**`、根 `pyproject.toml`；規格衝突或缺件 → 停手回報，不腦補。

## 【交付物】

PR 一個（分支建議 `codex/ticket-0009-fastapi-service`），說明含 D20 憲法聲明＋驗收勾選。**L0 票：CI 綠即可由決策者直接合併**（pr-scope 應標 L0＝僅 app/；若溢出守門路徑則自動升 L2）。
