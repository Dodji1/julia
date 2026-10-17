"""Application FastAPI. Lancement : `uvicorn backend.app.main:create_app --factory`."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend import __version__
from backend.app.config import Settings
from backend.app.errors import install_error_handlers, new_request_id
from backend.app.ratelimit import AnswerRateLimits
from backend.app.routes import ROUTERS
from backend.app.services import Services, build_services


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.services = services or build_services(settings)
        try:
            yield
        finally:
            app.state.services.close()

    app = FastAPI(
        title="Julia API",
        version=__version__,
        summary="Assistante juridique sourcée : fiscalité du Bénin (V0).",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings
    app.state.limits = AnswerRateLimits(
        client_per_minute=settings.rate_limit_client_per_minute,
        client_per_day=settings.rate_limit_client_per_day,
        ip_per_minute=settings.rate_limit_ip_per_minute,
        daily_budget=settings.daily_answer_budget,
    )

    @app.middleware("http")
    async def assign_request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = new_request_id()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "X-Client-Id"],
            expose_headers=["X-Request-ID", "Retry-After"],
        )
    install_error_handlers(app)
    for router in ROUTERS:
        app.include_router(router)
    return app
