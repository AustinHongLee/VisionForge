"""本機 FastAPI 服務層：UI↔Python 橋的 Python 側（ADR-0009）。"""

from __future__ import annotations

import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from visionforge_core.calibration import recalibrate
from visionforge_core.contracts import (
    AnnotationRevision,
    BBox,
    CalibrationSnapshot,
    Claim,
    Concept,
    ConceptDefinition,
    CoverageRecord,
    CoverageState,
    GoldenSetEntry,
    Label,
    MediaAssignment,
    MediaRecord,
    MediaSource,
    TaskRecord,
)
from visionforge_core.contracts.claims import Geometry
from visionforge_core.providers import InferenceRequest, VisionProvider
from visionforge_core.review import ClaimForReview, approve, list_pending, reject
from visionforge_core.storage import Project, open_project
from visionforge_core.storage.errors import ConflictError, NotFoundError
from visionforge_core.teaching import (
    add_annotation,
    add_concept,
    add_task,
    assign_media,
    edit_annotation,
    get_coverage,
    retract_annotation,
    set_coverage,
)
from visionforge_providers import OpenAIProviderError

from visionforge_app.export import ExportOutcome, export_dataset
from visionforge_app.importer import import_media
from visionforge_app.importer.errors import MediaImportError
from visionforge_app.processing import UnknownMediaError, process_media
from visionforge_app.processing.run import apply_latest_to_claims
from visionforge_app.provider_config import ProviderConfigurationError, load_provider
from visionforge_app.query import MediaPage, list_media, thumbnail_path


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ImportResponse(BaseModel):
    media_hash: str
    deduplicated: bool
    record: MediaRecord


class InferRequest(BaseModel):
    media_hash: str
    concepts: list[Concept] = Field(default_factory=list)


class InferResponse(BaseModel):
    claims: tuple[Claim, ...]
    provider_id: str


class ProcessRequest(BaseModel):
    media_hash: str
    concepts: list[Concept] = Field(default_factory=list)


class ProcessResponse(BaseModel):
    run_id: str
    claim_count: int
    decision_ref: str
    cost_ref: str


class PendingReviewItem(BaseModel):
    claim: Claim
    run_ref: str
    media_hash: str


class ApproveRequest(BaseModel):
    claim_id: str
    reviewer: str = Field(min_length=1, max_length=256)
    final_geometry: Geometry | None = None
    final_concept_raw_text: str | None = Field(default=None, min_length=1, max_length=512)


class RejectRequest(BaseModel):
    claim_id: str
    reviewer: str = Field(min_length=1, max_length=256)


class RejectResponse(BaseModel):
    event_id: str
    to_status: str


class GoldenRequest(BaseModel):
    label_id: str
    added_by: str = Field(min_length=1, max_length=256)


class ExportRequest(BaseModel):
    fmt: Literal["yolo", "coco"]


class ExportResponse(BaseModel):
    version_id: str
    fmt: Literal["yolo", "coco"]
    out_dir: str
    image_count: int
    label_count: int
    class_names: tuple[str, ...]


class CreateTaskRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class CreateConceptRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=128)
    aliases: tuple[str, ...] = ()


class AssignMediaRequest(BaseModel):
    source_group_id: str | None = Field(default=None, min_length=1, max_length=256)


class TeachRequest(BaseModel):
    media_hash: str
    concept_ids: tuple[str, ...] = ()
    source_group_id: str | None = Field(default=None, min_length=1, max_length=256)


class TeachResponse(BaseModel):
    run_id: str
    claims: tuple[Claim, ...]


class TeachingStateResponse(BaseModel):
    task: TaskRecord
    assignment: MediaAssignment
    concepts: tuple[ConceptDefinition, ...]
    coverage: tuple[CoverageRecord, ...]
    annotations: tuple[AnnotationRevision, ...]
    teacher_claims: tuple[Claim, ...]


class AddAnnotationRequest(BaseModel):
    task_id: str
    media_hash: str
    concept_id: str
    bbox: BBox | None = None
    source_claim_ref: str | None = None


class EditAnnotationRequest(BaseModel):
    concept_id: str
    bbox: BBox


class SetCoverageRequest(BaseModel):
    task_id: str
    media_hash: str
    concept_id: str
    state: CoverageState


_LOCAL_RENDERER_ORIGIN_RE = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
_CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_LOCAL_ACTOR = "local-user"


def _new_ulid() -> str:
    timestamp_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    value = (timestamp_ms << 80) | secrets.randbits(80)
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD32[value & 0b11111])
        value >>= 5
    return "".join(reversed(chars))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _claim_item(project: Project, claim_id: str) -> ClaimForReview:
    try:
        claim, run_ref, media_hash = project.runs.get_claim_context(claim_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": "claim_not_found"}) from exc
    return ClaimForReview(claim=claim, run_ref=run_ref, media_hash=media_hash)


def _provider_unavailable(exc: OpenAIProviderError) -> HTTPException:
    return HTTPException(
        status_code=502,
        detail={"error": "provider_unavailable", "message": str(exc)},
    )


def _provider_not_configured(exc: ProviderConfigurationError) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"error": "provider_not_configured", "message": str(exc)},
    )


def _review_conflict(exc: ConflictError) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={"error": "review_conflict", "message": str(exc)},
    )


def create_app(project: Project, provider: VisionProvider | None = None) -> FastAPI:
    """建立可測的 FastAPI app；不在 import 時啟動服務。"""

    app = FastAPI(title="VisionForge local API")
    app.add_middleware(
        CORSMiddleware,
        allow_headers=["content-type"],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_origin_regex=_LOCAL_RENDERER_ORIGIN_RE,
        allow_origins=["null"],
    )
    provider_override = provider
    project_root = project.root

    @contextmanager
    def request_project() -> Iterator[Project]:
        current = open_project(project_root)
        try:
            yield current
        finally:
            current.close()

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/media", response_model=MediaPage)
    def media(limit: int = Query(100, ge=0), offset: int = Query(0, ge=0)) -> MediaPage:
        with request_project() as current:
            return list_media(current, limit=limit, offset=offset)

    @app.get("/tasks", response_model=list[TaskRecord])
    def tasks() -> list[TaskRecord]:
        with request_project() as current:
            return current.tasks.list()

    @app.post("/tasks", response_model=TaskRecord)
    def create_task_endpoint(request: CreateTaskRequest) -> TaskRecord:
        try:
            with request_project() as current:
                return add_task(
                    current,
                    task_id=_new_ulid(),
                    name=request.name,
                    created_at=_utc_now(),
                )
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc

    @app.get("/tasks/{task_id}/concepts", response_model=list[ConceptDefinition])
    def concepts(task_id: str) -> list[ConceptDefinition]:
        try:
            with request_project() as current:
                current.tasks.get(task_id)
                return current.concepts.list_by_task(task_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail={"error": "task_not_found"}) from exc

    @app.post("/tasks/{task_id}/concepts", response_model=ConceptDefinition)
    def create_concept_endpoint(
        task_id: str, request: CreateConceptRequest
    ) -> ConceptDefinition:
        try:
            with request_project() as current:
                return add_concept(
                    current,
                    concept_id=_new_ulid(),
                    task_id=task_id,
                    display_name=request.display_name,
                    aliases=request.aliases,
                    created_at=_utc_now(),
                )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail={"error": "task_not_found"}) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc

    @app.post(
        "/tasks/{task_id}/media/{media_hash}", response_model=MediaAssignment
    )
    def assign_media_endpoint(
        task_id: str, media_hash: str, request: AssignMediaRequest
    ) -> MediaAssignment:
        try:
            with request_project() as current:
                return assign_media(
                    current,
                    task_id=task_id,
                    media_hash=media_hash,
                    source_group_id=request.source_group_id or media_hash,
                    assigned_at=_utc_now(),
                )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail={"error": "scope_not_found"}) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc

    @app.get(
        "/tasks/{task_id}/media/{media_hash}/teaching",
        response_model=TeachingStateResponse,
    )
    def teaching_state(task_id: str, media_hash: str) -> TeachingStateResponse:
        try:
            with request_project() as current:
                task_record = current.tasks.get(task_id)
                assignment = current.assignments.get(task_id, media_hash)
                if assignment is None:
                    raise NotFoundError("media assignment 不存在")
                concept_records = current.concepts.list_by_task(task_id)
                return TeachingStateResponse(
                    task=task_record,
                    assignment=assignment,
                    concepts=tuple(concept_records),
                    coverage=tuple(
                        get_coverage(
                            current,
                            task_id=task_id,
                            media_hash=media_hash,
                            concept_id=concept.concept_id,
                        )
                        for concept in concept_records
                    ),
                    annotations=tuple(
                        current.annotations.list_effective(task_id, media_hash)
                    ),
                    teacher_claims=tuple(
                        current.claim_teaching_context.latest_claims(task_id, media_hash)
                    ),
                )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail={"error": "scope_not_found"}) from exc

    @app.post("/tasks/{task_id}/teach", response_model=TeachResponse)
    def teach(task_id: str, request: TeachRequest) -> TeachResponse:
        try:
            with request_project() as current:
                task_record = current.tasks.get(task_id)
                selected = current.concepts.list_by_task(task_id)
                if request.concept_ids:
                    requested = set(request.concept_ids)
                    selected = [item for item in selected if item.concept_id in requested]
                    if len(selected) != len(requested):
                        raise NotFoundError("部分 Concept 不屬於此 Task")
                if not selected:
                    raise ConflictError("至少需要一個 Concept 才能請教師判讀")
                assign_media(
                    current,
                    task_id=task_record.task_id,
                    media_hash=request.media_hash,
                    source_group_id=request.source_group_id or request.media_hash,
                    assigned_at=_utc_now(),
                )
                name_map = {
                    name: concept.concept_id
                    for concept in selected
                    for name in (concept.display_name, *concept.aliases)
                }
                outcome = process_media(
                    current,
                    request.media_hash,
                    [Concept(raw_text=concept.display_name) for concept in selected],
                    provider=provider_override or load_provider(current),
                    teaching_task_id=task_id,
                    concept_ids_by_name=name_map,
                )
                return TeachResponse(run_id=outcome.run.run_id, claims=outcome.run.claims)
        except UnknownMediaError as exc:
            raise HTTPException(status_code=404, detail={"error": "media_not_found"}) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail={"error": "scope_not_found"}) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc
        except OpenAIProviderError as exc:
            raise _provider_unavailable(exc) from exc
        except ProviderConfigurationError as exc:
            raise _provider_not_configured(exc) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail={"error": str(exc)}) from exc

    @app.post("/annotations", response_model=AnnotationRevision)
    def create_annotation_endpoint(request: AddAnnotationRequest) -> AnnotationRevision:
        try:
            with request_project() as current:
                return add_annotation(
                    current,
                    revision_id=_new_ulid(),
                    annotation_id=_new_ulid(),
                    task_id=request.task_id,
                    media_hash=request.media_hash,
                    concept_id=request.concept_id,
                    bbox=request.bbox,
                    source_claim_ref=request.source_claim_ref,
                    created_by=_LOCAL_ACTOR,
                    created_at=_utc_now(),
                )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail={"error": "scope_not_found"}) from exc
        except (ConflictError, ValueError) as exc:
            raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc

    @app.patch("/annotations/{annotation_id}", response_model=AnnotationRevision)
    def edit_annotation_endpoint(
        annotation_id: str, request: EditAnnotationRequest
    ) -> AnnotationRevision:
        try:
            with request_project() as current:
                return edit_annotation(
                    current,
                    annotation_id=annotation_id,
                    revision_id=_new_ulid(),
                    concept_id=request.concept_id,
                    bbox=request.bbox,
                    created_by=_LOCAL_ACTOR,
                    created_at=_utc_now(),
                )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail={"error": "annotation_not_found"}) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc

    @app.delete("/annotations/{annotation_id}", response_model=AnnotationRevision)
    def retract_annotation_endpoint(annotation_id: str) -> AnnotationRevision:
        try:
            with request_project() as current:
                return retract_annotation(
                    current,
                    annotation_id=annotation_id,
                    revision_id=_new_ulid(),
                    created_by=_LOCAL_ACTOR,
                    created_at=_utc_now(),
                )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail={"error": "annotation_not_found"}) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc

    @app.put("/coverage", response_model=CoverageRecord)
    def set_coverage_endpoint(request: SetCoverageRequest) -> CoverageRecord:
        try:
            with request_project() as current:
                verified = request.state is not CoverageState.unverified
                return set_coverage(
                    current,
                    task_id=request.task_id,
                    media_hash=request.media_hash,
                    concept_id=request.concept_id,
                    state=request.state,
                    reviewer=_LOCAL_ACTOR if verified else None,
                    verified_at=_utc_now() if verified else None,
                )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail={"error": "scope_not_found"}) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc

    @app.get("/media/{media_hash}/thumbnail")
    def thumbnail(media_hash: str) -> FileResponse:
        with request_project() as current:
            path = thumbnail_path(current, media_hash)
        if path is None:
            raise HTTPException(status_code=404, detail={"error": "thumbnail_not_found"})
        return FileResponse(path, media_type="image/jpeg")

    @app.post("/import", response_model=ImportResponse)
    async def import_file(file: Annotated[UploadFile, File()]) -> ImportResponse:
        data = await file.read()
        source = MediaSource(kind="file", detail=file.filename or "upload")
        try:
            with request_project() as current:
                outcome = import_media(current, data, source)
        except MediaImportError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": exc.__class__.__name__, "message": str(exc)},
            ) from exc
        return ImportResponse(
            media_hash=outcome.media_hash,
            deduplicated=outcome.deduplicated,
            record=outcome.record,
        )

    @app.post("/infer", response_model=InferResponse)
    def infer(request: InferRequest) -> InferResponse:
        with request_project() as current:
            blob = current.blobs.find(request.media_hash)
            if blob is None:
                raise HTTPException(status_code=404, detail={"error": "media_not_found"})
            data = blob.read_bytes()
            try:
                active_provider = provider_override or load_provider(current)
            except ProviderConfigurationError as exc:
                raise _provider_not_configured(exc) from exc
            try:
                result = active_provider.infer(
                    data,
                    InferenceRequest(concepts=tuple(request.concepts)),
                )
            except OpenAIProviderError as exc:
                raise _provider_unavailable(exc) from exc
            claims = apply_latest_to_claims(current, result.claims)
        return InferResponse(claims=claims, provider_id=result.provider_id)

    @app.post("/process", response_model=ProcessResponse)
    def process(request: ProcessRequest) -> ProcessResponse:
        try:
            with request_project() as current:
                outcome = process_media(
                    current,
                    request.media_hash,
                    request.concepts,
                    provider=provider_override or load_provider(current),
                )
        except UnknownMediaError as exc:
            raise HTTPException(status_code=404, detail={"error": "media_not_found"}) from exc
        except OpenAIProviderError as exc:
            raise _provider_unavailable(exc) from exc
        except ProviderConfigurationError as exc:
            raise _provider_not_configured(exc) from exc
        run = outcome.run
        return ProcessResponse(
            run_id=run.run_id,
            claim_count=len(run.claims),
            decision_ref=run.decision_ref,
            cost_ref=run.cost_ref,
        )

    @app.get("/review/pending", response_model=list[PendingReviewItem])
    def review_pending() -> list[PendingReviewItem]:
        with request_project() as current:
            return [
                PendingReviewItem(
                    claim=item.claim,
                    run_ref=item.run_ref,
                    media_hash=item.media_hash,
                )
                for item in list_pending(current)
            ]

    @app.post("/review/approve", response_model=Label)
    def review_approve(request: ApproveRequest) -> Label:
        try:
            with request_project() as current:
                item = _claim_item(current, request.claim_id)
                return approve(
                    current,
                    item,
                    reviewer=request.reviewer,
                    reviewed_at=_utc_now(),
                    node_id=_new_ulid(),
                    label_id=_new_ulid(),
                    event_id=_new_ulid(),
                    final_geometry=request.final_geometry,
                    final_concept_raw_text=request.final_concept_raw_text,
                )
        except ConflictError as exc:
            raise _review_conflict(exc) from exc

    @app.post("/review/reject", response_model=RejectResponse)
    def review_reject(request: RejectRequest) -> RejectResponse:
        try:
            with request_project() as current:
                item = _claim_item(current, request.claim_id)
                event = reject(
                    current,
                    item,
                    reviewer=request.reviewer,
                    reviewed_at=_utc_now(),
                    event_id=_new_ulid(),
                )
                return RejectResponse(event_id=event.event_id, to_status=event.to_status.value)
        except ConflictError as exc:
            raise _review_conflict(exc) from exc

    @app.post("/golden", response_model=GoldenSetEntry)
    def golden(request: GoldenRequest) -> GoldenSetEntry:
        try:
            with request_project() as current:
                label = current.labels.get(request.label_id)
                entry = GoldenSetEntry(
                    entry_id=_new_ulid(),
                    media_hash=label.media_hash,
                    label_ref=label.label_id,
                    added_by=request.added_by,
                    added_at=_utc_now(),
                )
                current.golden.append(entry)
                return entry
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail={"error": "label_not_found"}) from exc

    @app.post("/recalibrate", response_model=CalibrationSnapshot)
    def recalibrate_endpoint() -> CalibrationSnapshot | Response:
        with request_project() as current:
            snapshot = recalibrate(
                current,
                calibration_id=_new_ulid(),
                created_at=_utc_now(),
                golden_manifest_ref=_new_ulid(),
            )
        if snapshot is None:
            return Response(status_code=204)
        return snapshot

    @app.post("/export", response_model=ExportResponse)
    def export_endpoint(request: ExportRequest) -> ExportResponse:
        try:
            with request_project() as current:
                outcome = export_dataset(
                    current,
                    request.fmt,
                    version_id=_new_ulid(),
                    created_at=_utc_now(),
                )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc
        return _export_response(outcome)

    return app


def _export_response(outcome: ExportOutcome) -> ExportResponse:
    return ExportResponse(
        version_id=outcome.version_id,
        fmt=outcome.fmt,
        out_dir=str(outcome.out_dir),
        image_count=outcome.image_count,
        label_count=outcome.label_count,
        class_names=outcome.class_names,
    )
