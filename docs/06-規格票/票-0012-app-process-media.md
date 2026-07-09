# 票-0012：app process_media——跑 provider 並入帳存 run

| 項目 | 內容 |
|---|---|
| 狀態 | 🟨 已發出（2026-07-08，審核飛輪 #1 的 app 側） |
| 承包 | Codex（Builder） |
| 審查層級 | **L0 免審**（app/ 白名單；帳本治理已由 core `record_inference_run` 封裝；CI 全綠＋D20 即由決策者合併） |
| 政策依據 | ADR-0010 #1；消費 core `visionforge_core.orchestrator.record_inference_run`（已合併）＋fixture provider＋儲存層 |

## 【目標】

實作有狀態的「process media」：取媒體位元組 → 跑 provider → **把結果交給 core orchestrator 入帳存成 InferenceRun**（Decision＋Cost＋Run＋Outcome 由 core 保證，D3/D4）→ 回傳 run。並加 `POST /process` 端點。既有無狀態 `/infer`（票-0009）保留為即時預覽。**帳本語彙不在本票操心——core 已封裝；app 只負責組 subject/producer/呼叫 provider。**

## 【範圍】（白名單）

`app/**`。新增 `app/src/visionforge_app/processing/run.py`、於 `app/src/visionforge_app/api/app.py` 加 `POST /process` 路由；`app/pyproject.toml` 可加 `python-ulid`（產 ULID）；測試於 `app/tests/`。

**不得動**：`core/**`（含 orchestrator/契約簽名）、`ui/**`、`.github/**`、`scripts/**`、根 `pyproject.toml`、`providers/**`。

## 【介面】（已凍結——只實作本體）

```python
# app/src/visionforge_app/processing/run.py
from dataclasses import dataclass
from visionforge_core.contracts import Concept, InferenceRun
from visionforge_core.storage import Project
from visionforge_core.providers import VisionProvider  # provisional

@dataclass(frozen=True)
class ProcessOutcome:
    run: InferenceRun

def process_media(
    project: Project,
    media_hash: str,
    concepts: list[Concept],
    *,
    provider: VisionProvider | None = None,   # 預設 FixtureProvider（票-0008）
    task: str = "detect",
    now: datetime | None = None,              # 測試可注入；預設 UTC now
    id_factory: Callable[[], str] | None = None,  # 測試可注入；預設產合法 ULID
) -> ProcessOutcome: ...
```

**消費 core（不得改）**：
```python
record_inference_run(project, *, subject, producer, task, claims, duration_ms,
                     run_id, decision_id, cost_id, outcome_id, now) -> InferenceRun
# subject=MediaSubject(media_hash, width_px, height_px)  ← 取自 project.media.get(media_hash)
# producer=Producer(provider_id, provider_version, params_hash)  ← 取自 provider.capability + 參數雜湊
```

## 【工作項】

1. 取 `record = project.media.get(media_hash)`（無 → 明確錯誤）；`data = project.blobs.find(media_hash)` 讀 bytes（無 → 錯誤）。
2. `provider = provider or FixtureProvider()`；`result = provider.infer(data, InferenceRequest(concepts=tuple(concepts)))`。
3. 組 `subject=MediaSubject(media_hash, record.width_px, record.height_px)`；`producer=Producer(provider_id=cap.provider_id, provider_version=cap.version, params_hash=sha256(規範化 concepts+task+version))`。
4. 產四個 ULID（run/decision/cost/outcome）與 `now`（可注入）；呼叫 `record_inference_run(...)`。
5. 回 `ProcessOutcome(run)`。
6. `POST /process` 端點：body `{media_hash, concepts:[Concept]}` → 呼叫 process_media → 回 `{run_id, claim_count, decision_ref, cost_ref}`（或整個 run 摘要）；未知 media_hash → 404。

## 【驗收】（測試清單＝完成的唯一定義）

1. 匯入一張圖後 `process_media(project, hash, [Concept(raw_text="bolt")])` → 回 run；`project.runs.get(run.run_id)` 存在、claims 非空、`concept.raw_text=="bolt"`。
2. **入帳完整**：`project.decisions.get(run.decision_ref).kind=="invoke_provider"`；`project.costs.iter_by_subject("run", run.run_id)` 有 1 筆；`iter_outcomes(run.decision_ref)` 有 1 筆 success。
3. **確定性**（注入固定 now＋id_factory）：同輸入兩次 → run.model_dump() 相等。
4. 未知 media_hash → 明確錯誤（服務層 ValueError／API 404），非 500。
5. `POST /process` {已匯入 hash, concepts:[{raw_text:"bolt"}]} → 200，回 run_id＋claim_count；未知 hash → 404。
6. `python scripts/check_forbidden_imports.py`、`ruff check app`、`pytest app/tests` 全綠。

## 【憲法】

ADR-0010（審核飛輪 #1）、D3/D4（每次調用有 Decision＋Cost——由 core orchestrator 保證，本票不得繞過自行組帳本）、D13（app→core/providers）、A5（注入 now/id 求可測確定性）、D14（缺媒體結構化報錯）。

## 【禁區】

不得改 `core/**`（含不得自行組 DecisionRecord/CostEntry——一律走 `record_inference_run`）；不得動 `ui/**`、`.github/**`、`scripts/**`、根 `pyproject.toml`、`providers/**`；不得綁非 loopback；規格衝突或缺件 → 停手回報，不腦補。

## 【交付物】

PR 一個（分支建議 `codex/ticket-0012-process-media`），說明含 D20 憲法聲明＋驗收勾選。**L0 票：CI 綠即可由決策者直接合併**（pr-scope 應標 L0＝僅 app/）。
