"""最小 Orchestrator：把一次 provider 調用記入帳本（ADR-0010 #1、憲法 D3/D4）。

每次調用都必須有可重放的 Decision＋入帳的 Cost（D3/D4）——本函式把「已產生的
推論結果」組成合法 DecisionRecord＋CostEntry＋InferenceRun＋成功 DecisionOutcome
並 append-only 落庫。**純 core：不 import providers**（provider 由 app 呼叫後把
claims 傳進來）。時間戳與 ULID 由呼叫端注入 → 可測、可重放（A5）。
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from visionforge_core.contracts import (
    CandidateProvider,
    Claim,
    CostAgent,
    CostEntry,
    CostMeasurement,
    DecisionChoice,
    DecisionOutcome,
    DecisionRecord,
    InferenceRun,
    InputRef,
    MediaSubject,
    PolicyRef,
    Producer,
)
from visionforge_core.storage import Project


def _policy_ref(label: str) -> PolicyRef:
    return PolicyRef(
        policy_hash=hashlib.sha256(label.encode("utf-8")).hexdigest(),
        policy_label=label,
    )


def record_inference_run(
    project: Project,
    *,
    subject: MediaSubject,
    producer: Producer,
    task: str,
    claims: Sequence[Claim],
    duration_ms: int,
    run_id: str,
    decision_id: str,
    cost_id: str,
    outcome_id: str,
    now: datetime,
    reason_code: str = "only_capable",
    policy_label: str = "m0-default",
    call_count: int = 1,
) -> InferenceRun:
    """組 Decision→Cost→Run→Outcome 並落庫（append-only），回傳 InferenceRun。"""
    decision = DecisionRecord(
        decision_id=decision_id,
        at=now,
        kind="invoke_provider",
        policy=_policy_ref(policy_label),
        inputs=(InputRef(kind="media", id=subject.media_hash),),
        candidates=(
            CandidateProvider(
                provider_id=producer.provider_id,
                provider_version=producer.provider_version,
                capability_ok=True,
            ),
        ),
        choice=DecisionChoice(
            target=f"{producer.provider_id}@{producer.provider_version}",
            reason_code=reason_code,
        ),
    )
    cost = CostEntry(
        cost_id=cost_id,
        at=now,
        phase="actual",
        subject=InputRef(kind="run", id=run_id),
        agent=CostAgent(
            kind="provider",
            id=producer.provider_id,
            version=producer.provider_version,
        ),
        measurements=(CostMeasurement(unit="provider_call", amount=Decimal(call_count)),),
    )
    run = InferenceRun(
        run_id=run_id,
        subject=subject,
        producer=producer,
        task=task,
        created_at=now,
        duration_ms=duration_ms,
        cost_ref=cost_id,
        decision_ref=decision_id,
        claims=tuple(claims),
    )
    outcome = DecisionOutcome(
        outcome_id=outcome_id,
        decision_ref=decision_id,
        at=now,
        status="success",
        produced_refs=(InputRef(kind="run", id=run_id),),
    )
    # append-only；順序：decision→cost→run(claims 原子)→outcome。
    project.decisions.append(decision)
    project.costs.append(cost)
    project.runs.append(run)
    project.decisions.append_outcome(outcome)
    return run
