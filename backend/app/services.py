"""Assemblage des composants selon la configuration : mode `fake` ou `postgres`."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from backend.app.config import EngineMode, RerankerMode, Settings
from backend.rag.engine import EngineSettings, RagEngine, load_system_prompt
from backend.rag.fake import DemoLLM, InMemoryRetriever, demo_passages
from backend.rag.interfaces import LLMProvider, LLMUnavailableError
from backend.rag.llm import ExtractiveLLM, FallbackLLM, OpenAICompatibleLLM
from backend.rag.models import NoopReranker
from backend.rag.types import LLMCompletion
from backend.stores import (
    Catalog,
    DocumentRecord,
    FeedbackStore,
    InMemoryCatalog,
    InMemoryFeedbackStore,
    InMemoryTraceStore,
    TraceStore,
)

logger = logging.getLogger(__name__)


@dataclass
class Services:
    engine: RagEngine
    catalog: Catalog
    traces: TraceStore
    feedback: FeedbackStore
    database_status: Callable[[], str]
    closers: list[Callable[[], None]] = field(default_factory=list)

    def close(self) -> None:
        for close in reversed(self.closers):
            try:
                close()
            except Exception:
                logger.exception("Échec à la fermeture d'un composant")


class UnconfiguredLLM:
    def complete_json(self, system: str, user: str) -> LLMCompletion:
        raise LLMUnavailableError("aucune clé LLM configurée (JULIA_LLM_API_KEY)")


def engine_settings(settings: Settings) -> EngineSettings:
    return EngineSettings(
        retrieve_k=settings.retrieve_k,
        context_k=settings.context_k,
        min_relevance=settings.min_relevance,
        reference_year=settings.reference_year,
        max_passage_chars=settings.max_passage_chars,
    )


def build_services(settings: Settings) -> Services:
    if settings.engine is EngineMode.FAKE:
        return build_fake_services(settings)
    return build_postgres_services(settings)


def build_fake_services(settings: Settings, llm: LLMProvider | None = None) -> Services:
    passages = demo_passages()
    engine = RagEngine(
        InMemoryRetriever(passages),
        NoopReranker(),
        llm or DemoLLM(),
        load_system_prompt(),
        engine_settings(settings),
    )
    first = passages[0]
    catalog = InMemoryCatalog(
        [
            DocumentRecord(
                document_id=first.document_id,
                title=first.document_title,
                domain="fiscal",
                country="BJ",
                document_type=first.document_type,
                source_level=first.source_level,
                version=first.version,
                status=first.status,
                file_path=None,
                has_text_layer=True,
                chunk_count=len(passages),
            )
        ],
        corpus_version="demo",
    )
    return Services(engine, catalog, InMemoryTraceStore(), InMemoryFeedbackStore(), lambda: "not_configured")


def build_postgres_services(settings: Settings) -> Services:
    from psycopg_pool import ConnectionPool

    from backend.db.catalog import PgCatalog
    from backend.db.migrate import migrate
    from backend.db.retriever import PgHybridRetriever
    from backend.db.stores import PgFeedbackStore, PgTraceStore, configure_connection, database_status
    from backend.rag.models import CrossEncoderReranker, build_embedder

    assert settings.database_url is not None  # garanti par Settings
    applied = migrate(settings.database_url)
    if applied:
        logger.info("Migrations appliquées : %s", ", ".join(applied))

    pool = ConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True},
        configure=configure_connection,
        open=True,
    )
    embedder = build_embedder(
        settings.embedding_model, device=settings.model_device, max_tokens=settings.embedding_max_tokens
    )
    reranker = (
        CrossEncoderReranker(settings.reranker_model, device=settings.model_device)
        if settings.reranker is RerankerMode.CROSS_ENCODER
        else NoopReranker()
    )
    llm = build_llm(settings)
    engine = RagEngine(
        PgHybridRetriever(pool, embedder), reranker, llm, load_system_prompt(), engine_settings(settings)
    )
    closers: list[Callable[[], None]] = [pool.close]
    if isinstance(llm, OpenAICompatibleLLM | FallbackLLM):
        closers.append(llm.close)
    return Services(
        engine,
        PgCatalog(pool),
        PgTraceStore(pool),
        PgFeedbackStore(pool),
        lambda: database_status(pool),
        closers,
    )


def build_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "extractive":
        logger.warning("Mode test sans LLM : les réponses citent les passages sans les rédiger.")
        return ExtractiveLLM()
    providers: list[LLMProvider] = []
    if settings.llm_api_key is not None:
        providers.append(
            OpenAICompatibleLLM(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key.get_secret_value(),
                model=settings.llm_model,
                timeout_s=settings.llm_timeout_s,
                max_tokens=settings.llm_max_tokens,
                extra_body=settings.llm_extra_body,
            )
        )
    if settings.llm_fallback_base_url and settings.llm_fallback_model and settings.llm_fallback_api_key:
        providers.append(
            OpenAICompatibleLLM(
                base_url=settings.llm_fallback_base_url,
                api_key=settings.llm_fallback_api_key.get_secret_value(),
                model=settings.llm_fallback_model,
                timeout_s=settings.llm_timeout_s,
                max_tokens=settings.llm_max_tokens,
                extra_body=settings.llm_fallback_extra_body,
            )
        )
    if not providers:
        logger.warning("Aucune clé LLM : /answers renverra 503 ; /search reste utilisable.")
        return UnconfiguredLLM()
    return providers[0] if len(providers) == 1 else FallbackLLM(providers)
