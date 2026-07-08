"""本機 FastAPI 服務層：UI↔Python 橋的 Python 側（ADR-0009）。"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from visionforge_core.contracts import Claim, Concept, MediaRecord, MediaSource
from visionforge_core.providers import InferenceRequest, VisionProvider
from visionforge_core.storage import Project, open_project
from visionforge_providers import FixtureProvider

from visionforge_app.importer import import_media
from visionforge_app.importer.errors import MediaImportError
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


_LOCAL_RENDERER_ORIGIN_RE = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"


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
    active_provider = provider or FixtureProvider()
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
        result = active_provider.infer(data, InferenceRequest(concepts=tuple(request.concepts)))
        return InferResponse(claims=result.claims, provider_id=result.provider_id)

    return app
