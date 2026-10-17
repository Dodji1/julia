"""Interfaces des étapes interchangeables du moteur.

L'équipe RAG améliore la qualité en fournissant de meilleures implémentations de ces interfaces,
sans toucher à l'orchestrateur ni à l'API.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from backend.rag.types import AnalyzedQuery, LLMCompletion, Passage, SearchFilters


class LLMUnavailableError(RuntimeError):
    """Aucun fournisseur LLM n'a pu produire de réponse exploitable."""


class Retriever(Protocol):
    def retrieve(self, query: AnalyzedQuery, filters: SearchFilters, limit: int) -> list[Passage]: ...


class Reranker(Protocol):
    def rerank(self, question: str, passages: Sequence[Passage], top_n: int) -> list[Passage]: ...


class LLMProvider(Protocol):
    def complete_json(self, system: str, user: str) -> LLMCompletion:
        """Renvoie un objet JSON sous forme de texte ; lève `LLMUnavailableError` en cas d'échec."""
        ...


class Embedder(Protocol):
    model_name: str
    dimension: int

    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...
