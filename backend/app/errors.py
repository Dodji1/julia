"""Format d'erreur unique : {"error": {"code", "message", "request_id"}}."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.rag.interfaces import LLMUnavailableError

logger = logging.getLogger(__name__)

_HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers or {}


def new_request_id() -> str:
    return uuid.uuid4().hex


def request_id_of(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = new_request_id()
        request.state.request_id = request_id
    return request_id


def error_response(
    request: Request, status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    request_id = request_id_of(request)
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
        headers={**(headers or {}), "X-Request-ID": request_id},
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, error: ApiError) -> JSONResponse:
        return error_response(request, error.status_code, error.code, error.message, error.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        first = error.errors()[0] if error.errors() else {}
        location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
        detail = f" : {location} ({first.get('msg')})" if location else ""
        return error_response(request, 422, "VALIDATION_ERROR", f"Requête invalide{detail}.")

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(error.status_code, "HTTP_ERROR")
        message = (
            "Corps de requête illisible : JSON invalide ou texte non encodé en UTF-8."
            if error.status_code == 400
            else str(error.detail)
        )
        return error_response(request, error.status_code, code, message)

    @app.exception_handler(LLMUnavailableError)
    async def _llm_unavailable(request: Request, error: LLMUnavailableError) -> JSONResponse:
        logger.error("LLM indisponible (requête %s) : %s", request_id_of(request), error)
        return error_response(
            request,
            503,
            "LLM_UNAVAILABLE",
            "Le service de génération est momentanément indisponible. Réessayez dans quelques instants.",
            {"Retry-After": "30"},
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, error: Exception) -> JSONResponse:
        logger.exception("Erreur interne (requête %s)", request_id_of(request), exc_info=error)
        return error_response(request, 500, "INTERNAL_ERROR", "Erreur interne du moteur Julia.")
