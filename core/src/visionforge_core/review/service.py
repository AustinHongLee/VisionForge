"""審核狀態機（ADR-0010 #3、憲法 D7）：Claim → Label／ReviewEvent。

D7：Human Review 是 Claim→Label 的唯一通道。claims 為 append-only（不可改），
故審核狀態不靠改 claim，而靠事件與 Label 存在性推導——「待審」＝尚無 ReviewEvent。
approve 時經 Taxonomy `ensure` 把概念映射到節點（Label 不變量：概念須映射）。
純 core：不 import providers。ULID／時間由呼叫端注入 → 可測、可重放（A5）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from visionforge_core.contracts import (
    Claim,
    Concept,
    ConceptMappingProvenance,
    Label,
    ReviewEvent,
    ReviewStatus,
    TaxonomyNode,
)
from visionforge_core.contracts.claims import Geometry
from visionforge_core.storage import Project
from visionforge_core.storage.errors import ConflictError


@dataclass(frozen=True)
class ClaimForReview:
    """待審 claim 及其血統參照（run_ref／media_hash 由儲存層帶出）。"""

    claim: Claim
    run_ref: str
    media_hash: str


def list_pending(project: Project) -> list[ClaimForReview]:
    """列出待審 claim（尚無 ReviewEvent）。分組由呼叫端/UI 依概念處理。"""
    return [ClaimForReview(c, run_ref, media_hash) for c, run_ref, media_hash in
            project.runs.iter_pending_review()]


def _mapped_concept(
    project: Project, raw_text: str, *, node_id: str, reviewer: str, now: datetime
) -> Concept:
    node = project.taxonomy.ensure(TaxonomyNode(node_id=node_id, raw_text=raw_text, created_at=now))
    return Concept(
        raw_text=raw_text,
        taxonomy_node_id=node.node_id,
        mapping_provenance=ConceptMappingProvenance(kind="human", actor=reviewer, mapped_at=now),
    )


def _authoritative_item(project: Project, item: ClaimForReview) -> ClaimForReview:
    claim, run_ref, media_hash = project.runs.get_claim_context(item.claim.claim_id)
    if item.run_ref != run_ref or item.media_hash != media_hash or item.claim != claim:
        raise ConflictError("Claim 的 run／media 關聯與持久化資料不一致")
    if project.review_events.iter_by_claim(claim.claim_id):
        raise ConflictError(f"claim {claim.claim_id} 已有終局審核結果")
    return ClaimForReview(claim=claim, run_ref=run_ref, media_hash=media_hash)


def approve(
    project: Project,
    item: ClaimForReview,
    *,
    reviewer: str,
    reviewed_at: datetime,
    node_id: str,
    label_id: str,
    event_id: str,
    final_geometry: Geometry | None = None,
    final_concept_raw_text: str | None = None,
) -> Label:
    """批准（含就地修正）：產 Label＋ReviewEvent（D7）。

    傳 final_geometry 或 final_concept_raw_text 之一即視為 edited_approved。
    """
    with project.db.transaction():
        item = _authoritative_item(project, item)
        edited = final_geometry is not None or final_concept_raw_text is not None
        geometry = final_geometry if final_geometry is not None else item.claim.geometry
        raw_text = final_concept_raw_text or item.claim.concept.raw_text
        concept = _mapped_concept(
            project, raw_text, node_id=node_id, reviewer=reviewer, now=reviewed_at
        )
        source_status = "edited_approved" if edited else "approved"
        label = Label(
            label_id=label_id,
            claim_ref=item.claim.claim_id,
            run_ref=item.run_ref,
            media_hash=item.media_hash,
            assertion=item.claim.assertion,
            final_geometry=geometry,
            final_concept=concept,
            reviewer=reviewer,
            reviewed_at=reviewed_at,
            source_status=source_status,
        )
        to_status = ReviewStatus.edited_approved if edited else ReviewStatus.approved
        event = ReviewEvent(
            event_id=event_id,
            at=reviewed_at,
            actor=reviewer,
            claim_ref=item.claim.claim_id,
            from_status=item.claim.review.status,
            to_status=to_status,
            label_ref=label_id,
        )
        project.labels.append(label)
        project.review_events.append(event)
    return label


def reject(
    project: Project,
    item: ClaimForReview,
    *,
    reviewer: str,
    reviewed_at: datetime,
    event_id: str,
) -> ReviewEvent:
    """否決：只產 ReviewEvent（不產 Label，契約不變量已擋）。"""
    with project.db.transaction():
        item = _authoritative_item(project, item)
        event = ReviewEvent(
            event_id=event_id,
            at=reviewed_at,
            actor=reviewer,
            claim_ref=item.claim.claim_id,
            from_status=item.claim.review.status,
            to_status=ReviewStatus.rejected,
        )
        project.review_events.append(event)
    return event
