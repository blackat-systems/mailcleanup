from __future__ import annotations

from contextlib import suppress
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from mailmap import __version__
from mailmap.map_api import install_map_api
from mailmap.map_fixtures import ensure_synthetic_map_fixture
from mailmap.map_model import MapCompositionError
from mailmap.repository import Repository
from mailmap.service import MailmapService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "mailmap-base-segura.db"
PlanOperation = Literal["trash", "archive", "unsubscribe"]


def _default_operations() -> list[PlanOperation]:
    return ["trash"]


class PlanRequest(BaseModel):
    source_ids: list[str] = Field(alias="sourceIds", min_length=1, max_length=100)
    before_date: date | None = Field(default=None, alias="beforeDate")
    keep_latest: int = Field(default=0, alias="keepLatest", ge=0, le=50)
    operations: list[PlanOperation] = Field(default_factory=_default_operations, min_length=1)

    model_config = {"populate_by_name": True}


def create_app(db_path: Path | None = None, *, serve_frontend: bool = True) -> FastAPI:
    repository = Repository(db_path or DEFAULT_DB_PATH)
    service = MailmapService(repository)
    app = FastAPI(
        title="Mailmap local",
        description="API local de Base Segura. Sólo contiene datos sintéticos.",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        swagger_ui_oauth2_redirect_url=None,
    )
    app.state.repository = repository
    app.state.service = service
    # La API v1 permanece disponible; la puerta v2 devolverá map_unavailable.
    with suppress(MapCompositionError):
        ensure_synthetic_map_fixture(repository)

    @app.get("/api/v1/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "mode": "synthetic",
            "version": __version__,
            "gmailConnected": False,
        }

    @app.get("/api/v1/dashboard")
    def dashboard() -> dict[str, object]:
        return service.dashboard()

    @app.get("/api/v1/analysis")
    def analysis() -> dict[str, object]:
        return service.analysis_status()

    @app.get("/api/v1/sources")
    def sources(
        query: str | None = Query(default=None, max_length=120),
        rubro: str | None = Query(default=None, max_length=80),
        view: Literal["all", "subscriptions", "spam", "protected"] = "all",
    ) -> list[dict[str, object]]:
        return service.sources(query=query, rubro=rubro, view=view)

    @app.get("/api/v1/sources/{source_id}")
    def source(source_id: str) -> dict[str, object]:
        record = service.source(source_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Fuente sintética no encontrada")
        return record

    @app.post("/api/v1/plans/preview", status_code=201)
    def preview_plan(request: PlanRequest) -> dict[str, object]:
        known_ids = {str(item["id"]) for item in service.sources()}
        unknown = sorted(set(request.source_ids) - known_ids)
        if unknown:
            raise HTTPException(
                status_code=422,
                detail={"message": "Hay fuentes desconocidas", "sourceIds": unknown},
            )
        return service.create_plan(
            source_ids=request.source_ids,
            before_date=request.before_date,
            keep_latest=request.keep_latest,
            operations=list(request.operations),
        )

    @app.post("/api/v1/plans/{plan_id}/revalidate")
    def revalidate_plan(plan_id: str) -> dict[str, object]:
        result = service.revalidate_plan(plan_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Plan simulado no encontrado")
        return result

    @app.get("/api/v1/history")
    def history() -> list[dict[str, object]]:
        return service.history()

    @app.get("/api/v1/configuration")
    def configuration() -> dict[str, object]:
        return service.configuration()

    install_map_api(app, repository)

    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    if serve_frontend and frontend_dist.exists():
        assets = frontend_dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def frontend(full_path: str) -> FileResponse:
            candidate = (frontend_dist / full_path).resolve()
            if (
                full_path
                and candidate.is_relative_to(frontend_dist.resolve())
                and candidate.is_file()
            ):
                return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")
    else:

        @app.get("/", include_in_schema=False)
        def root() -> dict[str, str]:
            return {
                "message": "API sintética activa. Construí frontend/ para servir la interfaz.",
                "openapi": "/api/openapi.json",
            }

    return app


app = create_app()
