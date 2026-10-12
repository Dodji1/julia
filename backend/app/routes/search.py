from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.app.dependencies import ServicesDep, require_admin
from backend.app.errors import request_id_of
from backend.app.schemas import ErrorResponse, SearchHit, SearchRequest, SearchResponse, document_url
from backend.rag.types import SearchFilters

router = APIRouter(prefix="/api/v1", tags=["équipe"])


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Recherche seule, sans LLM (débogage et évaluation du retrieval)",
    dependencies=[Depends(require_admin)],
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def search(payload: SearchRequest, request: Request, services: ServicesDep) -> SearchResponse:
    filters = SearchFilters(domain=payload.filters.domain, jurisdiction=payload.filters.jurisdiction)
    passages = services.engine.search(payload.query, filters, payload.limit)
    return SearchResponse(
        request_id=request_id_of(request),
        results=[
            SearchHit(
                chunk_id=passage.chunk_id,
                document_id=passage.document_id,
                title=passage.document_title,
                article=passage.article,
                page=passage.page,
                version=passage.version,
                location=passage.location,
                status=passage.status,
                source_level=passage.source_level,
                relevance=passage.relevance,
                exact_match=passage.exact_match,
                excerpt=passage.content,
                document_url=document_url(passage.document_id, passage.page),
                is_ocr=passage.is_ocr,
            )
            for passage in passages
        ],
    )
