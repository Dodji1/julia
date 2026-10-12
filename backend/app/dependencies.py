"""Dépendances FastAPI partagées par les routes."""

from __future__ import annotations

import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, Request

from backend.app.config import Settings
from backend.app.errors import ApiError
from backend.app.ratelimit import AnswerRateLimits, RateLimited
from backend.app.services import Services


def get_services(request: Request) -> Services:
    return request.app.state.services


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_limits(request: Request) -> AnswerRateLimits:
    return request.app.state.limits


ServicesDep = Annotated[Services, Depends(get_services)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
LimitsDep = Annotated[AnswerRateLimits, Depends(get_limits)]


def client_ip(request: Request) -> str:
    """IP du client. Derrière Caddy, uvicorn la lit dans X-Forwarded-For (--proxy-headers)."""
    return request.client.host if request.client else "unknown"


def client_hash(settings: Settings, ip: str) -> str:
    """Empreinte salée de l'IP : permet de compter les visiteurs sans stocker leur adresse."""
    salted = f"{settings.trace_salt.get_secret_value()}:{ip}".encode()
    return hashlib.sha256(salted).hexdigest()[:16]


def as_api_error(error: RateLimited) -> ApiError:
    return ApiError(429, error.code, error.message, {"Retry-After": str(error.retry_after_s)})


def require_admin(request: Request, settings: SettingsDep) -> None:
    """Routes réservées à l'équipe. Sans jeton configuré (développement uniquement), accès libre ;
    en production, `Settings` refuse de démarrer sans `JULIA_ADMIN_TOKEN`."""
    if settings.admin_token is None:
        return
    provided = request.headers.get("X-Admin-Token", "").encode()
    if not secrets.compare_digest(provided, settings.admin_token.get_secret_value().encode()):
        raise ApiError(401, "UNAUTHORIZED", "Jeton d'administration manquant ou invalide.")
