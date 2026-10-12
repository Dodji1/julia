import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.ratelimit import AnswerRateLimits, DailyBudget, RateLimited, SlidingWindowLimiter
from backend.rag.analyzer import analyze
from backend.rag.context import build_context
from backend.rag.fake import InMemoryRetriever, ScriptedLLM
from backend.rag.interfaces import LLMUnavailableError
from backend.rag.llm import FallbackLLM, OpenAICompatibleLLM
from backend.rag.types import AnalyzedQuery, SearchFilters
from contracts import LegalChunk, article_key

# --- Analyse de la question ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Que dit l'article 224 du CGI ?", ("224",)),
        ("Voir l'art. 1085 ter et l'article 12 - 1", ("1085 ter", "12-1")),
        ("Articles 5 bis", ("5 bis",)),
        ("Les artisans paient-ils la TPS ?", ()),
    ],
)
def test_analyzer_detects_article_references(question, expected):
    assert analyze(question, reference_year=2026).article_keys == expected


def test_analyzer_includes_archives_for_past_years():
    assert analyze("Quel était le taux en 2024 ?", reference_year=2026).include_archived is True
    assert analyze("Quel est le taux en 2026 ?", reference_year=2026).include_archived is False


def test_article_key_normalization():
    assert article_key("Art.  1085   Ter") == "1085 ter"
    assert article_key("Article 12 - 1") == "12-1"
    assert article_key(None) is None


# --- Contrat LegalChunk -------------------------------------------------------------------

VALID_CHUNK = {
    "chunk_id": "cgi-2026:art-224",
    "document_id": "cgi-2026",
    "ordinal": 0,
    "content": "Texte de l'article.",
    "source_level": 1,
    "country": "BJ",
    "document_type": "code_ou_loi",
    "document_title": "Code général des impôts",
    "status": "en_vigueur",
    "title": "Livre II",
    "chapter": "Chapitre III",
    "article": "224",
    "tags": ["tva", " Exoneration ", "TVA"],
}


def test_legal_chunk_normalizes_tags_and_builds_location():
    chunk = LegalChunk.model_validate(VALID_CHUNK)

    assert chunk.tags == ["TVA", "EXONERATION"]
    assert chunk.location == "Livre II › Chapitre III"
    assert chunk.article_key == "224"


@pytest.mark.parametrize(
    "change",
    [
        {"chunk_id": "x"},
        {"status": "active"},
        {"source_level": 5},
        {"page_start": 10, "page_end": 9},
        {"champ_inconnu": 1},
        {"content": "   "},
    ],
)
def test_legal_chunk_rejects_invalid_data(change):
    with pytest.raises(ValidationError):
        LegalChunk.model_validate({**VALID_CHUNK, **change})


# --- Contexte LLM -------------------------------------------------------------------------


def test_context_labels_archived_and_ocr_passages(make_passage):
    context, labelled = build_context([make_passage(1), make_passage(2, status="archive", is_ocr=True)])

    assert list(labelled) == ["P1", "P2"]
    assert "archivé, ne décrit pas le droit en vigueur" in context
    assert context.count("reconnaissance optique") == 1


# --- Recherche factice --------------------------------------------------------------------


def test_in_memory_retriever_excludes_archives_unless_requested(make_passage):
    current = make_passage(1, content="taux de TVA")
    archived = make_passage(2, content="taux de TVA", status="archive")
    retriever = InMemoryRetriever([current, archived])
    filters = SearchFilters("fiscal", "BJ")

    now = retriever.retrieve(AnalyzedQuery(text="taux TVA"), filters, 10)
    past = retriever.retrieve(AnalyzedQuery(text="taux TVA", include_archived=True), filters, 10)

    assert [p.chunk_id for p in now] == [current.chunk_id]
    assert len(past) == 2


# --- Limitation de débit ------------------------------------------------------------------


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_sliding_window_limiter():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=2, window_s=60, clock=clock)

    assert limiter.hit("a") is None
    assert limiter.hit("a") is None
    assert limiter.hit("a") == pytest.approx(60)
    assert limiter.hit("b") is None
    clock.now += 61
    assert limiter.hit("a") is None


def test_daily_budget_resets_at_midnight_utc():
    now = datetime(2026, 11, 23, 23, 0, tzinfo=UTC)
    budget = DailyBudget(limit=1, now=lambda: now)

    assert budget.consume() is None
    assert budget.consume() == pytest.approx(3600)
    now += timedelta(hours=2)
    assert budget.consume() is None


def test_invalid_client_id_falls_back_to_the_ip():
    limits = AnswerRateLimits(client_per_minute=1, client_per_day=10, ip_per_minute=100, daily_budget=100)

    limits.check_answer("<script>", "1.2.3.4")
    with pytest.raises(RateLimited):
        limits.check_answer(None, "1.2.3.4")


# --- Fournisseurs LLM ---------------------------------------------------------------------


def _llm(handler):
    client = httpx.Client(base_url="https://llm.test", transport=httpx.MockTransport(handler))
    return OpenAICompatibleLLM(
        base_url="https://llm.test", api_key="k", model="deepseek-flash",
        extra_body={"thinking": {"type": "disabled"}}, client=client,
    )


def test_openai_compatible_llm_sends_json_mode_without_thinking():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "model": "deepseek-flash",
            "choices": [{"message": {"content": '{"status": "answered"}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 300},
        })

    completion = _llm(handler).complete_json("système", "utilisateur")

    assert seen["path"] == "/chat/completions"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["thinking"] == {"type": "disabled"}
    assert seen["body"]["messages"][0] == {"role": "system", "content": "système"}
    assert (completion.input_tokens, completion.output_tokens) == (1200, 300)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text="erreur"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": "{"}, "finish_reason": "length"}]}),
    ],
)
def test_openai_compatible_llm_failures_raise_unavailable(response):
    with pytest.raises(LLMUnavailableError):
        _llm(lambda request: response).complete_json("s", "u")


def test_fallback_llm_uses_the_next_provider():
    primary = ScriptedLLM([LLMUnavailableError("principal en panne")])
    secondary = ScriptedLLM(['{"ok": true}'])

    assert FallbackLLM([primary, secondary]).complete_json("s", "u").text == '{"ok": true}'


def test_fallback_llm_reports_every_failure():
    providers = [ScriptedLLM([LLMUnavailableError("A")]), ScriptedLLM([LLMUnavailableError("B")])]

    with pytest.raises(LLMUnavailableError, match="A ; B"):
        FallbackLLM(providers).complete_json("s", "u")


# --- Configuration ------------------------------------------------------------------------


def test_production_refuses_an_incomplete_configuration():
    with pytest.raises(ValidationError, match="JULIA_ADMIN_TOKEN"):
        Settings(_env_file=None, env="prod", engine="postgres", database_url="postgresql://x", llm_api_key="k")


def test_postgres_engine_requires_a_database_url():
    with pytest.raises(ValidationError, match="JULIA_DATABASE_URL"):
        Settings(_env_file=None, engine="postgres")
