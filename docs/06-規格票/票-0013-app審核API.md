# 票-0013：app 審核 API——把審核狀態機接成 HTTP

| 項目 | 內容 |
|---|---|
| 狀態 | 🟨 已發出（2026-07-08，審核飛輪 #3 的 app 側＋#4 黃金集升級） |
| 承包 | Codex（Builder） |
| 審查層級 | **L0 免審**（app/ 白名單；D7 狀態機已由 core `visionforge_core.review` 封裝；CI 全綠＋D20 即由決策者合併） |
| 政策依據 | ADR-0010 #3/#4；消費 core `review.list_pending/approve/reject`（已合併）＋`GoldenSetEntry`／`project.golden` |

## 【目標】

把 core 審核狀態機接成本機 API：列待審、批准（含就地修正）、否決、把 Label 升級為黃金集。**D7／帳本語彙都在 core，app 只做傳輸與 ULID/時間注入。** 供之後「整理」站 UI 消費。

## 【範圍】（白名單）

`app/**`。於 `app/src/visionforge_app/api/app.py` 加審核路由；必要時 `app/src/visionforge_app/review/`（薄封裝）；測試於 `app/tests/`。可用已加入的 `python-ulid`。

**不得動**：`core/**`（含 review/契約簽名）、`ui/**`、`.github/**`、`scripts/**`、根/providers `pyproject.toml`。

## 【介面】（端點契約已凍結——回應型別重用契約生成物）

| 方法 | 路徑 | 請求 | 回應 |
|---|---|---|---|
| GET | `/review/pending` | — | `[{ "claim": Claim, "run_ref": str, "media_hash": str }, ...]`（來自 `review.list_pending`） |
| POST | `/review/approve` | `{ claim_id, run_ref, media_hash, reviewer, final_geometry?: Geometry, final_concept_raw_text?: str }` | `Label` |
| POST | `/review/reject` | `{ claim_id, run_ref, media_hash, reviewer }` | `{ event_id, to_status }` |
| POST | `/golden` | `{ label_id, added_by }` | `GoldenSetEntry` |

**消費 core（不得改）**：
```python
from visionforge_core.review import ClaimForReview, approve, list_pending, reject
# approve(project, item, *, reviewer, reviewed_at, node_id, label_id, event_id,
#         final_geometry=None, final_concept_raw_text=None) -> Label
# reject(project, item, *, reviewer, reviewed_at, event_id) -> ReviewEvent
```

## 【工作項】

1. `/review/pending`：`review.list_pending(project)` → 序列化（`claim` 用 Claim 契約）。
2. `/review/approve`：`claim = project.runs.get_claim(claim_id)`（無→404）；組 `ClaimForReview(claim, run_ref, media_hash)`；產 `node_id/label_id/event_id`（ULID）與 `reviewed_at`（now）；呼叫 `review.approve(...)` → 回 Label。
3. `/review/reject`：同上組 item，產 `event_id`＋now → `review.reject(...)` → 回 `{event_id, to_status}`。
4. `/golden`：`label = project.labels.get(label_id)`（無→404）；`GoldenSetEntry(entry_id=ULID, media_hash=label.media_hash, label_ref=label_id, added_by, added_at=now, status="active")` → `project.golden.append(...)` → 回該筆。
5. 例外→結構化：未知 claim/label → 404；驗證失敗（如概念空）→ 422，非 500。

## 【驗收】（測試清單＝完成的唯一定義；TestClient）

1. 匯入圖＋`POST /process` 產生 claims 後，`GET /review/pending` 回非空、每項有 claim/run_ref/media_hash。
2. `POST /review/approve`（帶 pending 的 refs）→ 200 回 Label，`final_concept.taxonomy_node_id` 非空；之後該 claim 不再出現在 `/review/pending`。
3. `POST /review/approve` 帶 `final_geometry` → Label `source_status=="edited_approved"`。
4. `POST /review/reject` → 200；該 claim 不再 pending；未產 Label。
5. `POST /golden`（帶上一步的 label_id）→ 200 回 GoldenSetEntry（status active、label_ref 正確）。
6. 未知 claim_id/label_id → 404；不是 500。
7. `python scripts/check_forbidden_imports.py`、`ruff check app`、`pytest app/tests` 全綠。

## 【憲法】

ADR-0010（審核飛輪 #3/#4）、D7（Claim→Label 只經 core review，app 不得自組 Label）、D8（黃金集登記）、D13（app→core）、A5（注入 ULID/now 求可測）、D14（結構化 404/422）、唯一事實來源（回應重用 Claim/Label/GoldenSetEntry 契約）。

## 【禁區】

不得改 `core/**`（含不得自行組 Label/ReviewEvent——一律走 `visionforge_core.review`）；不得動 `ui/**`、`.github/**`、`scripts/**`、根/providers `pyproject.toml`；不得綁非 loopback；不得手寫與契約平行的回應型別；規格衝突或缺件 → 停手回報，不腦補。

## 【交付物】

PR 一個（分支建議 `codex/ticket-0013-review-api`），說明含 D20 憲法聲明＋驗收勾選。**L0 票：CI 綠即可由決策者直接合併**（pr-scope 應標 L0＝僅 app/）。
