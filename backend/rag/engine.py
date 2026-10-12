"""Orchestrateur RAG : analyse → recherche → reranking → garde 1 → LLM → garde 2.

Les deux gardes sont du code, pas des consignes de prompt :
- garde 1 : si aucun passage n'atteint le seuil de pertinence, on refuse sans appeler le LLM ;
- garde 2 : une réponse « answered » sans aucune citation vérifiable est transformée en refus.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from backend.rag import messages
from backend.rag.analyzer import analyze
from backend.rag.citations import strip_citations, verify_citations
from backend.rag.context import build_context, build_user_message
from backend.rag.interfaces import LLMProvider, LLMUnavailableError, Reranker, Retriever
from backend.rag.types import AnswerStatus, EngineResult, EngineTrace, Passage, SearchFilters

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"
_LLM_ATTEMPTS = 2


def load_system_prompt(name: str = "answer_system.md") -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


@dataclass(frozen=True, slots=True)
class EngineSettings:
    retrieve_k: int = 30
    context_k: int = 8
    min_relevance: float = 0.45
    reference_year: int = 2026


class RagEngine:
    def __init__(
        self,
        retriever: Retriever,
        reranker: Reranker,
        llm: LLMProvider,
        system_prompt: str,
        settings: EngineSettings | None = None,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._llm = llm
        self._system_prompt = system_prompt
        self._settings = settings or EngineSettings()

    def search(self, question: str, filters: SearchFilters, limit: int) -> list[Passage]:
        """Recherche seule, sans LLM : débogage et évaluation du retrieval."""
        query = analyze(question, self._settings.reference_year)
        candidates = self._retriever.retrieve(query, filters, max(limit, self._settings.retrieve_k))
        return self._reranker.rerank(query.text, candidates, limit)

    def answer(self, question: str, filters: SearchFilters) -> EngineResult:
        trace = EngineTrace()
        query = analyze(question, self._settings.reference_year)

        with _timed(trace, "retrieve"):
            candidates = self._retriever.retrieve(query, filters, self._settings.retrieve_k)
        with _timed(trace, "rerank"):
            passages = self._reranker.rerank(query.text, candidates, self._settings.context_k)
        trace.retrieved = list(passages)

        if not self._is_relevant_enough(passages):
            return _insufficient(trace)

        context, labelled = build_context(passages)
        with _timed(trace, "generate"):
            status, markdown = self._generate(build_user_message(query.text, context), trace)

        if status is AnswerStatus.INSUFFICIENT_SOURCES:
            return _insufficient(trace)
        if status is AnswerStatus.CLARIFICATION_REQUIRED:
            return EngineResult(status, strip_citations(markdown), (), trace)

        verified = verify_citations(markdown, labelled)
        trace.discarded_citations = list(verified.discarded)
        if verified.discarded:
            logger.warning("Citations écartées par la garde 2 : %s", ", ".join(verified.discarded))
        if not verified.sources:
            return _insufficient(trace)
        return EngineResult(AnswerStatus.ANSWERED, verified.answer_markdown, verified.sources, trace)

    def _is_relevant_enough(self, passages: list[Passage]) -> bool:
        threshold = self._settings.min_relevance
        return any(
            passage.exact_match or (passage.relevance is not None and passage.relevance >= threshold)
            for passage in passages
        )

    def _generate(self, user_message: str, trace: EngineTrace) -> tuple[AnswerStatus, str]:
        last_error: ValueError | None = None
        for attempt in range(1, _LLM_ATTEMPTS + 1):
            completion = self._llm.complete_json(self._system_prompt, user_message)
            trace.llm_model = completion.model
            trace.input_tokens = _add(trace.input_tokens, completion.input_tokens)
            trace.output_tokens = _add(trace.output_tokens, completion.output_tokens)
            try:
                return parse_llm_answer(completion.text)
            except ValueError as error:
                last_error = error
                logger.warning("Sortie LLM invalide (tentative %d) : %s", attempt, error)
        raise LLMUnavailableError(f"sortie LLM invalide après {_LLM_ATTEMPTS} tentatives : {last_error}")


def parse_llm_answer(text: str) -> tuple[AnswerStatus, str]:
    try:
        payload = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON illisible : {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("un objet JSON est attendu")

    try:
        status = AnswerStatus(payload.get("status"))
    except ValueError:
        raise ValueError(f"statut inconnu : {payload.get('status')!r}") from None

    markdown = payload.get("answer_markdown")
    if not isinstance(markdown, str):
        raise ValueError("answer_markdown manquant")
    if status is not AnswerStatus.INSUFFICIENT_SOURCES and not markdown.strip():
        raise ValueError("answer_markdown vide")
    return status, markdown.strip()


def _insufficient(trace: EngineTrace) -> EngineResult:
    return EngineResult(AnswerStatus.INSUFFICIENT_SOURCES, messages.INSUFFICIENT_SOURCES, (), trace)


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        stripped = stripped.removesuffix("```").strip()
    return stripped


def _add(total: int | None, value: int | None) -> int | None:
    if value is None:
        return total
    return (total or 0) + value


@contextmanager
def _timed(trace: EngineTrace, stage: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        trace.timings_ms[stage] = round((time.perf_counter() - start) * 1000)
