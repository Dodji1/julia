"""Modèles HTTP : c'est le contrat de l'API (exporté dans `docs/api/openapi.json`).

Compatibilité avec le client du frontend V0 : les champs ajoutés par rapport à
`frontend-contract.yaml` (chunk_id, location, source_level, document_type) sont ignorés par sa
validation Zod ; aucun champ existant n'a changé de nom ni de type.
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceStatus = Literal["en_vigueur", "archive", "a_verifier"]
AnswerStatusLiteral = Literal["answered", "insufficient_sources", "clarification_required"]


def document_url(document_id: str, page: int | None = None) -> str:
    """URL relative du PDF original ; `#page=N` est compris par les lecteurs PDF des navigateurs."""
    url = f"/api/v1/documents/{quote(document_id, safe='')}/file"
    return f"{url}#page={page}" if page else url


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnswerFilters(_Strict):
    domain: Literal["fiscal"]
    jurisdiction: Literal["BJ"]


class AnswerRequest(_Strict):
    question: str = Field(min_length=3, max_length=4000)
    filters: AnswerFilters

    @field_validator("question")
    @classmethod
    def _strip(cls, question: str) -> str:
        stripped = question.strip()
        if len(stripped) < 3:
            raise ValueError("la question doit contenir au moins 3 caractères")
        return stripped


class AnswerSource(_Strict):
    citation_id: str = Field(pattern=r"^[1-9][0-9]*$", description="Numéro utilisé dans [1], [2]…")
    chunk_id: str
    document_id: str
    title: str
    article: str | None
    page: int | None = Field(ge=1)
    version: str | None
    location: str | None = Field(description="Livre › Chapitre › Section, quand il est connu.")
    status: SourceStatus
    source_level: int = Field(ge=1, le=4, description="1 texte officiel … 4 documentation secondaire.")
    document_type: str
    excerpt: str = Field(description="Extrait exact relu dans la base documentaire, jamais généré.")
    document_url: str = Field(description="Ouvre le PDF original, à la page citée (#page=N).")
    is_ocr: bool


class AnswerResponse(_Strict):
    request_id: str
    conversation_id: str
    status: AnswerStatusLiteral
    answer_markdown: str
    sources: list[AnswerSource]


class ErrorBody(_Strict):
    code: str
    message: str
    request_id: str


class ErrorResponse(_Strict):
    error: ErrorBody


class SearchRequest(_Strict):
    query: str = Field(min_length=3, max_length=4000)
    filters: AnswerFilters
    limit: int = Field(default=10, ge=1, le=50)


class SearchHit(_Strict):
    chunk_id: str
    document_id: str
    title: str
    article: str | None
    page: int | None
    version: str | None
    location: str | None
    status: SourceStatus
    source_level: int
    relevance: float | None
    exact_match: bool
    excerpt: str
    document_url: str
    is_ocr: bool


class SearchResponse(_Strict):
    request_id: str
    results: list[SearchHit]


class DocumentSummary(_Strict):
    document_id: str
    title: str
    domain: str
    country: str
    document_type: str
    source_level: int
    version: str | None
    status: SourceStatus
    is_ocr: bool
    chunk_count: int
    document_url: str


class DocumentListResponse(_Strict):
    corpus_version: str | None
    documents: list[DocumentSummary]


class FeedbackRequest(_Strict):
    request_id: str = Field(min_length=1, max_length=64)
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=1000)


class HealthResponse(_Strict):
    status: Literal["ok", "degraded"]
    version: str
    engine: str
    database: Literal["ok", "down", "not_configured"]
    corpus_version: str | None
