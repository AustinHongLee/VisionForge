# 票-0007：app media 查詢服務（list_media／get_media／thumbnail_path）

| 項目 | 內容 |
|---|---|
| 狀態 | 🟨 已發出（2026-07-08，並行雙軌） |
| 承包 | Codex（Builder） |
| 審查層級 | **L0 免審**（app/ 白名單；CI 全綠＋D20 聲明即由決策者直接合併，協議 §3-2） |
| 政策依據 | 建於已合併的 `MediaRepository.iter_recent`（ADR-0007 隨附，commit ad3914c）與儲存層（ADR-0005） |

## 【目標】

在服務層提供 media 的分頁列表、單筆取得與縮圖路徑查詢，供 UI 匯入頁之後接後端消費。**純 app、只讀、消費既有凍結 core 介面，不觸及 core。**

## 【範圍】（白名單）

`app/**`。實作 `app/src/visionforge_app/query/media.py`（新檔）＋於服務層 `__init__` 匯出公開名；測試與測試資料於 `app/tests/`。

**不得動**：`core/**`、`.github/**`、`scripts/**`、根 `pyproject.toml`、任何凍結守門測試。

## 【介面】（已凍結——只實作本體，不得改簽名）

```python
# app/src/visionforge_app/query/media.py
from dataclasses import dataclass
from pathlib import Path
from visionforge_core.contracts import MediaRecord

@dataclass(frozen=True)
class MediaPage:
    items: tuple[MediaRecord, ...]
    total: int          # 專案內 media 總數（project.media.count()）
    limit: int
    offset: int
    has_more: bool      # offset + len(items) < total

def list_media(project: Project, *, limit: int = 100, offset: int = 0) -> MediaPage: ...

def get_media(project: Project, media_hash: str) -> MediaRecord | None:
    """存在回 MediaRecord，不存在回 None（不拋 NotFoundError）。"""

def thumbnail_path(project: Project, media_hash: str) -> Path | None:
    """縮圖檔存在才回其路徑；否則 None。路徑＝project.root/"media"/"thumbs"/{media_hash}.jpg"""
```

**消費（不修改）既有凍結介面**：`project.media.iter_recent(limit=, offset=)`、`project.media.get(media_hash)`（不存在拋 `NotFoundError`，本服務需捕捉轉 None）、`project.media.count()`、`project.root`（Path）。

## 【工作項】

1. `list_media`：`items = project.media.iter_recent(limit=limit, offset=offset)`；`total = project.media.count()`；`has_more = offset + len(items) < total`；回 `MediaPage`。
2. `get_media`：try `project.media.get(media_hash)`；捕捉 `NotFoundError` → 回 `None`。
3. `thumbnail_path`：組 `project.root / "media" / "thumbs" / f"{media_hash}.jpg"`；`.is_file()` 為真回該路徑，否則 `None`。
4. `limit`/`offset` 為負 → 拋 `ValueError`（防呆，在查詢前）。

## 【驗收】（測試清單＝完成的唯一定義）

1. 建專案、加入數筆 media（用既有匯入或直接 `project.media.add`），`list_media(limit=2, offset=0)` 回前 2 筆、`total` 正確、`has_more=True`；`offset` 翻頁不重不漏；末頁 `has_more=False`。
2. 排序與 `iter_recent` 一致（最近匯入優先）——本票不重定義排序，只驗證委派正確。
3. `get_media` 命中回 MediaRecord；未命中回 `None`（**不得拋例外**）。
4. `thumbnail_path`：縮圖檔存在回路徑、不存在回 `None`。
5. `limit=-1` 或 `offset=-1` → `ValueError`。
6. 空專案 `list_media` → `items=()`、`total=0`、`has_more=False`。
7. `python scripts/check_forbidden_imports.py`、`ruff check app`、`pytest app/tests` 全綠。

## 【憲法】

只讀服務（不寫帳本）、D1（core 消費限服務層，方向 app→core）、A5（分頁確定性委派 iter_recent 的排序）、D14（缺件以 `None`／`ValueError` 明確表達，不吞不腦補）。

## 【禁區】

不得改任何凍結簽名／型別；不得動 `core/**`（含不得為查詢在 core 加方法——如需新查詢能力，回報由 Architect 於 core 補）、`.github/**`、`scripts/**`；不得讓 `get_media` 對未命中拋例外（介面要求回 None）；規格衝突或缺件 → 停手回報，不腦補。

## 【交付物】

PR 一個（分支建議 `codex/ticket-0007-media-query`），說明含 D20 憲法聲明＋驗收勾選。**L0 票：CI 綠即可由決策者直接合併**（若動到 `core/**` 或守門路徑則自動升 L2）。
