"""Tests d'intégration sur un vrai PostgreSQL + pgvector.

Lancement : docker compose up -d db, puis
    JULIA_TEST_DATABASE_URL=postgresql://julia:julia-dev@127.0.0.1:55432/julia_test pytest -m db
La base désignée est entièrement vidée : ne jamais pointer vers une base de travail.
"""

from __future__ import annotations

import os

import psycopg
import pytest
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from backend.db.catalog import PgCatalog
from backend.db.migrate import migrate
from backend.db.retriever import PgHybridRetriever
from backend.db.stores import PgFeedbackStore, PgTraceStore, configure_connection
from backend.indexing.index_corpus import index_corpus
from backend.indexing.manifest import Manifest, ManifestEntry
from backend.rag.analyzer import analyze
from backend.rag.engine import RagEngine
from backend.rag.fake import HashingEmbedder, ScriptedLLM
from backend.rag.models import NoopReranker
from backend.rag.types import AnswerStatus, SearchFilters
from backend.stores import RetrievedHit, TraceRecord
from contracts import LegalChunk

pytestmark = pytest.mark.db

FILTERS = SearchFilters(domain="fiscal", jurisdiction="BJ")


def _entry(document_id, country="BJ", status="en_vigueur", **extra):
    return ManifestEntry(
        id=document_id, path=f"{document_id}.pdf", title=document_id, domain="fiscal", country=country,
        document_type="code_ou_loi", source_level=1, status=status, has_text_layer=True, in_mvp=True, **extra,
    )


MANIFEST = Manifest(
    source_root="ressources",
    entries={
        "cgi-2026": _entry("cgi-2026", version_label="2026"),
        "cgi-2025": _entry("cgi-2025", status="archive", version_label="2025"),
        "ohada-au": _entry("ohada-au", country="OHADA"),
        "senegal": _entry("senegal", country="SN"),
    },
)


def _chunk(document_id, ordinal, content, article=None, status="en_vigueur", country="BJ"):
    return LegalChunk(
        chunk_id=f"{document_id}:{ordinal}", document_id=document_id, ordinal=ordinal, content=content,
        source_level=1, country=country, document_type="code_ou_loi", document_title=document_id.upper(),
        status=status, article=article, page_start=ordinal + 1,
    )


CHUNKS = [
    _chunk("cgi-2026", 0, "Le taux de la taxe sur la valeur ajoutée est fixé par la loi.", article="224"),
    _chunk("cgi-2026", 1, "L'impôt sur les sociétés est dû par les personnes morales.", article="1"),
    _chunk("cgi-2025", 0, "Ancien taux de la taxe sur la valeur ajoutée.", article="224", status="archive"),
    _chunk("ohada-au", 0, "Les sociétés commerciales tiennent une comptabilité.", country="OHADA"),
    _chunk("senegal", 0, "Taxe sur la valeur ajoutée au Sénégal.", country="SN"),
]


@pytest.fixture(scope="module")
def database_url():
    url = os.environ.get("JULIA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("JULIA_TEST_DATABASE_URL non défini")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    assert migrate(url) == ["001_init"]
    assert migrate(url) == []
    with psycopg.connect(url) as conn:
        register_vector(conn)
        report = index_corpus(conn, CHUNKS, MANIFEST, HashingEmbedder(), corpus_version="test-1")
    assert (report.documents, report.chunks) == (4, 5)
    return url


@pytest.fixture(scope="module")
def pool(database_url):
    with ConnectionPool(database_url, kwargs={"autocommit": True}, configure=configure_connection) as pool:
        yield pool


@pytest.fixture(scope="module")
def retriever(pool):
    return PgHybridRetriever(pool, HashingEmbedder())


def _ids(passages):
    return [passage.chunk_id for passage in passages]


def test_exact_article_comes_first(retriever):
    passages = retriever.retrieve(analyze("Que prévoit l'article 224 ?", 2026), FILTERS, 10)

    assert passages[0].chunk_id == "cgi-2026:0"
    assert passages[0].exact_match is True


def test_full_text_search_ignores_accents(pool):
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT chunk_id FROM chunks WHERE content_tsv @@ plainto_tsquery('french_unaccent', %s)",
            ("impot societes",),
        ).fetchall()

    assert [row[0] for row in rows] == ["cgi-2026:1"]


def test_archives_are_excluded_unless_the_question_targets_the_past(retriever):
    current = retriever.retrieve(analyze("taux de la taxe sur la valeur ajoutée", 2026), FILTERS, 10)
    past = retriever.retrieve(analyze("taux de la taxe sur la valeur ajoutée en 2025", 2026), FILTERS, 10)

    assert "cgi-2025:0" not in _ids(current)
    assert "cgi-2025:0" in _ids(past)


def test_community_law_is_applicable_but_foreign_law_is_not(retriever):
    passages = retriever.retrieve(analyze("sociétés commerciales comptabilité taxe", 2026), FILTERS, 10)

    assert "ohada-au:0" in _ids(passages)
    assert "senegal:0" not in _ids(passages)


def test_vector_branch_provides_a_relevance(retriever):
    passages = retriever.retrieve(analyze("taux de la taxe sur la valeur ajoutée", 2026), FILTERS, 10)

    assert passages[0].relevance is not None and 0 < passages[0].relevance <= 1


def test_engine_answers_from_postgres(retriever, llm_json):
    llm = ScriptedLLM([llm_json("answered", "Le taux est fixé par la loi [P1].")])
    engine = RagEngine(retriever, NoopReranker(), llm, "consignes")

    result = engine.answer("taux de la taxe sur la valeur ajoutée article 224", FILTERS)

    assert result.status is AnswerStatus.ANSWERED
    assert result.sources[0].content == CHUNKS[0].content


def test_catalog(pool):
    catalog = PgCatalog(pool)

    documents = {document.document_id: document for document in catalog.list_documents()}

    assert documents["cgi-2026"].chunk_count == 2
    assert documents["cgi-2026"].file_path == "ressources/cgi-2026.pdf"
    assert catalog.get_document("inconnu") is None
    assert catalog.corpus_version() == "test-1"


def test_reindexing_a_document_replaces_its_chunks(database_url):
    replacement = [_chunk("cgi-2026", 0, "Nouvelle rédaction de l'article.", article="224")]
    with psycopg.connect(database_url) as conn:
        register_vector(conn)
        index_corpus(conn, replacement, MANIFEST, HashingEmbedder(), corpus_version="test-2")
        count = conn.execute("SELECT count(*) FROM chunks WHERE document_id = 'cgi-2026'").fetchone()[0]
        others = conn.execute("SELECT count(*) FROM chunks WHERE document_id <> 'cgi-2026'").fetchone()[0]
        # Remettre le corpus initial pour les autres tests du module.
        index_corpus(conn, CHUNKS[:2], MANIFEST, HashingEmbedder(), corpus_version="test-3")

    assert (count, others) == (1, 3)


def test_traces_and_feedback_are_stored(pool):
    PgTraceStore(pool).record(
        TraceRecord(
            request_id="req-1", question="Q", filters={"domain": "fiscal"}, status="answered",
            retrieved=[RetrievedHit("cgi-2026:0", 0.8, False)], cited=["cgi-2026:0"], timings_ms={"generate": 12},
        )
    )
    PgFeedbackStore(pool).add("req-1", 1, None)

    with pool.connection() as conn:
        trace = conn.execute("SELECT retrieved, cited FROM rag_traces WHERE request_id = 'req-1'").fetchone()
        rating = conn.execute("SELECT rating FROM feedback WHERE request_id = 'req-1'").fetchone()[0]

    assert trace == ([{"chunk_id": "cgi-2026:0", "relevance": 0.8, "exact_match": False}], ["cgi-2026:0"])
    assert rating == 1
