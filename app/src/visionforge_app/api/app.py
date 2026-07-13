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
    CalibrationSnapshot,
    Claim,
    Concept,
    GoldenSetEntry,
    Label,
    MediaRecord,
    MediaSource,
)
from visionforge_core.contracts.claims import Geometry
from visionforge_core.providers import InferenceRequest, VisionProvider
from visionforge_core.review import ClaimForReview, approve, list_pending, reject
from visionforge_core.storage import Project, open_project
from visionforge_core.storage.errors import ConflictError, NotFoundError
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


_LOCAL_RENDERER_ORIGIN_RE = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
_CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


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
        allow_methods=["GET", "POST"],
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
