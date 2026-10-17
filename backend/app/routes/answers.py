from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Request

from backend.app.dependencies import (
    LimitsDep,
    ServicesDep,
    SettingsDep,
    as_api_error,
    client_hash,
    client_ip,
)
from backend.app.errors import new_request_id, request_id_of
from backend.app.ratelimit import RateLimited
from backend.app.schemas import AnswerRequest, AnswerResponse, AnswerSource, ErrorResponse, document_url
from backend.rag.interfaces import LLMUnavailableError
from backend.rag.types import Passage, SearchFilters
from backend.stores import RetrievedHit, TraceRecord, record_safely

router = APIRouter(prefix="/api/v1", tags=["answers"])


@router.post(
    "/answers",
    response_model=AnswerResponse,
    summary="Répondre à une question juridique à partir du corpus",
    responses={
        422: {"model": ErrorResponse, "description": "Requête invalide"},
        429: {"model": ErrorResponse, "description": "Limite de débit ou quota du jour atteint"},
        500: {"model": ErrorResponse, "description": "Erreur interne"},
        503: {"model": ErrorResponse, "description": "Fournisseur LLM indisponible"},
    },
)
def create_answer(
    payload: AnswerRequest,
    request: Request,
    background: BackgroundTasks,
    services: ServicesDep,
    settings: SettingsDep,
    limits: LimitsDep,
) -> AnswerResponse:
    ip = client_ip(request)
    try:
        limits.check_answer(request.headers.get("X-Client-Id"), ip)
    except RateLimited as error:
        raise as_api_error(error) from None

    request_id = request_id_of(request)
    filters = SearchFilters(domain=payload.filters.domain, jurisdiction=payload.filters.jurisdiction)
    common = {
        "request_id": request_id,
        "question": payload.question,
        "filters": payload.filters.model_dump(),
        "client_hash": client_hash(settings, ip),
    }
    try:
        result = services.engine.answer(payload.question, filters)
    except LLMUnavailableError as error:
        record_safely(services.traces, TraceRecord(**common, status="error", error=str(error)))
        raise

    trace = result.trace
    background.add_task(
        record_safely,
        services.traces,
        TraceRecord(
            **common,
            status=result.status.value,
            retrieved=[RetrievedHit(p.chunk_id, p.relevance, p.exact_match) for p in trace.retrieved],
            cited=[passage.chunk_id for passage in result.sources],
            timings_ms=trace.timings_ms,
            llm_model=trace.llm_model,
            input_tokens=trace.input_tokens,
            output_tokens=trace.output_tokens,
        ),
    )
    return AnswerResponse(
        request_id=request_id,
        conversation_id=new_request_id(),
        status=result.status.value,
        answer_markdown=result.answer_markdown,
        sources=[_source(number, passage) for number, passage in enumerate(result.sources, start=1)],
    )


def _source(number: int, passage: Passage) -> AnswerSource:
    return AnswerSource(
        citation_id=str(number),
        chunk_id=passage.chunk_id,
        document_id=passage.document_id,
        title=passage.document_title,
        article=passage.article,
        page=passage.page,
        version=passage.version,
        location=passage.location,
        status=passage.status,
        source_level=passage.source_level,
        document_type=passage.document_type,
        excerpt=passage.content,
        document_url=document_url(passage.document_id, passage.page),
        is_ocr=passage.is_ocr,
    )
