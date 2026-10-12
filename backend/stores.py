"""Stockages utilisés par l'API : catalogue documentaire, traces et retours utilisateurs.

Les implémentations Postgres sont dans `backend.db` ; les implémentations en mémoire servent au
mode `fake` et aux tests.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    document_id: str
    title: str
    domain: str
    country: str
    document_type: str
    source_level: int
    version: str | None
    status: str
    file_path: str | None
    has_text_layer: bool
    chunk_count: int = 0


@dataclass(frozen=True, slots=True)
class RetrievedHit:
    chunk_id: str
    relevance: float | None
    exact_match: bool


@dataclass(frozen=True, slots=True)
class TraceRecord:
    request_id: str
    question: str
    filters: dict[str, Any]
    status: str
    retrieved: list[RetrievedHit] = field(default_factory=list)
    cited: list[str] = field(default_factory=list)
    timings_ms: dict[str, int] = field(default_factory=dict)
    llm_model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None
    client_hash: str | None = None


class Catalog(Protocol):
    def list_documents(self) -> list[DocumentRecord]: ...

    def get_document(self, document_id: str) -> DocumentRecord | None: ...

    def corpus_version(self) -> str | None: ...


class TraceStore(Protocol):
    def record(self, trace: TraceRecord) -> None: ...


class FeedbackStore(Protocol):
    def add(self, request_id: str, rating: int, comment: str | None) -> None: ...


def record_safely(store: TraceStore, trace: TraceRecord) -> None:
    """Une trace perdue ne doit jamais faire échouer une réponse ; l'échec est journalisé."""
    try:
        store.record(trace)
    except Exception:
        logger.exception("Échec d'enregistrement de la trace %s", trace.request_id)


class InMemoryCatalog:
    def __init__(self, documents: list[DocumentRecord], corpus_version: str | None = None) -> None:
        self._documents = {document.document_id: document for document in documents}
        self._corpus_version = corpus_version

    def list_documents(self) -> list[DocumentRecord]:
        return sorted(self._documents.values(), key=lambda doc: (doc.source_level, doc.title))

    def get_document(self, document_id: str) -> DocumentRecord | None:
        return self._documents.get(document_id)

    def corpus_version(self) -> str | None:
        return self._corpus_version


class InMemoryTraceStore:
    def __init__(self) -> None:
        self.traces: list[TraceRecord] = []
        self._lock = threading.Lock()

    def record(self, trace: TraceRecord) -> None:
        with self._lock:
            self.traces.append(trace)


class InMemoryFeedbackStore:
    def __init__(self) -> None:
        self.entries: list[tuple[str, int, str | None]] = []
        self._lock = threading.Lock()

    def add(self, request_id: str, rating: int, comment: str | None) -> None:
        with self._lock:
            self.entries.append((request_id, rating, comment))
