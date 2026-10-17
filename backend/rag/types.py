"""Types échangés entre les étapes du moteur RAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_SOURCES = "insufficient_sources"
    CLARIFICATION_REQUIRED = "clarification_required"


@dataclass(frozen=True, slots=True)
class SearchFilters:
    domain: str
    jurisdiction: str


@dataclass(frozen=True, slots=True)
class AnalyzedQuery:
    text: str
    article_keys: tuple[str, ...] = ()
    years: tuple[int, ...] = ()
    include_archived: bool = False
    document_patterns: tuple[str, ...] = ()
    """Motifs SQL LIKE sur document_id (« %code-general-des-impots% ») quand la question nomme
    un texte : la recherche par numéro d'article se limite alors à ces documents."""


@dataclass(frozen=True, slots=True)
class Passage:
    """Un chunk retrouvé, avec ce qu'il faut pour le contexte LLM et pour la citation.

    `content` vient toujours de la base documentaire : c'est l'extrait affiché à l'utilisateur.
    `relevance` est un score dans [0, 1] (similarité cosinus, ou score du reranker) ; `None` quand
    le passage n'a été trouvé que par la recherche plein texte.
    """

    chunk_id: str
    document_id: str
    document_title: str
    content: str
    status: str
    source_level: int
    document_type: str
    version: str | None = None
    location: str | None = None
    article: str | None = None
    page: int | None = None
    is_ocr: bool = False
    relevance: float | None = None
    exact_match: bool = False


@dataclass(frozen=True, slots=True)
class LLMCompletion:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(slots=True)
class EngineTrace:
    timings_ms: dict[str, int] = field(default_factory=dict)
    retrieved: list[Passage] = field(default_factory=list)
    llm_model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    discarded_citations: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EngineResult:
    status: AnswerStatus
    answer_markdown: str
    sources: tuple[Passage, ...]
    """Dans l'ordre des numéros de citation : `sources[0]` correspond à [1]."""
    trace: EngineTrace
