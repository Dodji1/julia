from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from backend.app.dependencies import LimitsDep, ServicesDep, SettingsDep, as_api_error, client_ip
from backend.app.errors import ApiError
from backend.app.ratelimit import RateLimited
from backend.app.schemas import DocumentListResponse, DocumentSummary, ErrorResponse, document_url
from backend.stores import DocumentRecord

router = APIRouter(prefix="/api/v1", tags=["documents"])

_NOT_FOUND = {404: {"model": ErrorResponse, "description": "Document inconnu ou fichier absent"}}


@router.get("/documents", response_model=DocumentListResponse, summary="Corpus couvert par Julia")
def list_documents(services: ServicesDep) -> DocumentListResponse:
    return DocumentListResponse(
        corpus_version=services.catalog.corpus_version(),
        documents=[_summary(document) for document in services.catalog.list_documents()],
    )


@router.get("/documents/{document_id}", response_model=DocumentSummary, responses=_NOT_FOUND)
def get_document(document_id: str, services: ServicesDep) -> DocumentSummary:
    return _summary(_find(services, document_id))


@router.get(
    "/documents/{document_id}/file",
    response_class=FileResponse,
    summary="PDF original (ajouter #page=N pour ouvrir à une page)",
    responses={200: {"content": {"application/pdf": {}}}, **_NOT_FOUND},
)
def get_document_file(
    document_id: str, request: Request, services: ServicesDep, settings: SettingsDep, limits: LimitsDep
) -> FileResponse:
    try:
        limits.check_ip(client_ip(request))
    except RateLimited as error:
        raise as_api_error(error) from None

    document = _find(services, document_id)
    path = resolve_document_file(settings.data_raw_dir, document.file_path)
    if path is None:
        raise ApiError(404, "DOCUMENT_FILE_NOT_FOUND", "Le fichier original de ce document est indisponible.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
        content_disposition_type="inline",
        headers={"Cache-Control": "public, max-age=86400"},
    )


def resolve_document_file(raw_dir: Path, file_path: str | None) -> Path | None:
    """Chemin du PDF, à condition qu'il existe et reste sous `raw_dir`."""
    if not file_path:
        return None
    base = raw_dir.resolve()
    candidate = (base / file_path).resolve()
    if not candidate.is_relative_to(base) or not candidate.is_file():
        return None
    return candidate


def _find(services: ServicesDep, document_id: str) -> DocumentRecord:
    document = services.catalog.get_document(document_id)
    if document is None:
        raise ApiError(404, "DOCUMENT_NOT_FOUND", "Document inconnu.")
    return document


def _summary(document: DocumentRecord) -> DocumentSummary:
    return DocumentSummary(
        document_id=document.document_id,
        title=document.title,
        domain=document.domain,
        country=document.country,
        document_type=document.document_type,
        source_level=document.source_level,
        version=document.version,
        status=document.status,
        is_ocr=not document.has_text_layer,
        chunk_count=document.chunk_count,
        document_url=document_url(document.document_id),
    )
