from __future__ import annotations

from fastapi import APIRouter, Request, Response

from backend.app.dependencies import LimitsDep, ServicesDep, as_api_error, client_ip
from backend.app.ratelimit import RateLimited
from backend.app.schemas import ErrorResponse, FeedbackRequest

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post(
    "/feedback",
    status_code=204,
    summary="Avis de l'utilisateur sur une réponse (pouce levé ou baissé)",
    responses={422: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def create_feedback(
    payload: FeedbackRequest, request: Request, services: ServicesDep, limits: LimitsDep
) -> Response:
    try:
        limits.check_ip(client_ip(request))
    except RateLimited as error:
        raise as_api_error(error) from None
    services.feedback.add(payload.request_id, 1 if payload.rating == "up" else -1, payload.comment)
    return Response(status_code=204)
