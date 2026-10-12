from __future__ import annotations

import logging

from fastapi import APIRouter, Response

from backend import __version__
from backend.app.dependencies import ServicesDep, SettingsDep
from backend.app.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["exploitation"])


@router.get("/api/health", response_model=HealthResponse, summary="État de l'API et de la base")
def health(services: ServicesDep, settings: SettingsDep, response: Response) -> HealthResponse:
    database = services.database_status()
    corpus_version = None
    if database != "down":
        try:
            corpus_version = services.catalog.corpus_version()
        except Exception:
            logger.exception("Lecture de la version du corpus impossible")
            database = "down"
    if database == "down":
        response.status_code = 503
    return HealthResponse(
        status="degraded" if database == "down" else "ok",
        version=__version__,
        engine=settings.engine.value,
        database=database,
        corpus_version=corpus_version,
    )
