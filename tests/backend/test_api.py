from contextlib import ExitStack
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services import build_fake_services
from backend.rag.fake import ScriptedLLM
from backend.rag.interfaces import LLMUnavailableError
from backend.stores import DocumentRecord, InMemoryCatalog
from scripts.export_openapi import OPENAPI_PATH, render_openapi

QUESTION = {"question": "Quel est le taux de TVA applicable ?", "filters": {"domain": "fiscal", "jurisdiction": "BJ"}}
# Champs exigés par le client Zod du frontend V0 (docs/api/frontend-contract.yaml).
FRONTEND_ANSWER_FIELDS = {"request_id", "conversation_id", "status", "answer_markdown", "sources"}
FRONTEND_SOURCE_FIELDS = {
    "citation_id", "document_id", "title", "article", "page", "version", "status", "excerpt",
    "document_url", "is_ocr",
}


@pytest.fixture
def api():
    stack = ExitStack()

    def start(llm=None, catalog=None, raise_server_exceptions=True, **overrides):
        settings = Settings(_env_file=None, **overrides)
        services = build_fake_services(settings, llm=llm)
        if catalog is not None:
            services.catalog = catalog
        app = create_app(settings, services)
        client = stack.enter_context(TestClient(app, raise_server_exceptions=raise_server_exceptions))
        return client, services

    yield start
    stack.close()


def test_answer_follows_the_contract(api):
    client, services = api()

    response = client.post("/api/v1/answers", json=QUESTION)

    assert response.status_code == 200
    body = response.json()
    assert FRONTEND_ANSWER_FIELDS <= body.keys()
    assert body["status"] == "answered"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert "[1]" in body["answer_markdown"] and "[P1]" not in body["answer_markdown"]
    source = body["sources"][0]
    assert FRONTEND_SOURCE_FIELDS <= source.keys()
    assert source["citation_id"] == "1"
    assert source["excerpt"].startswith("Passage de démonstration")
    assert source["document_url"] == "/api/v1/documents/demo-cgi-2026/file#page=1"
    assert source["source_level"] == 1

    [trace] = services.traces.traces
    assert trace.status == "answered"
    assert trace.cited == [source["chunk_id"]]
    assert trace.client_hash and trace.client_hash != "testclient"


def test_question_without_relevant_source_is_refused(api):
    client, _ = api()

    body = client.post("/api/v1/answers", json={**QUESTION, "question": "Bonjour, comment allez-vous ?"}).json()

    assert body["status"] == "insufficient_sources"
    assert body["sources"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {**QUESTION, "extra": True},
        {**QUESTION, "filters": {"domain": "social", "jurisdiction": "BJ"}},
        {**QUESTION, "question": "  a  "},
        {"question": "Quel est le taux ?"},
    ],
)
def test_invalid_requests_use_the_error_format(api, payload):
    client, _ = api()

    response = client.post("/api/v1/answers", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_unreadable_body_is_a_bad_request(api):
    client, _ = api()

    response = client.post(
        "/api/v1/answers", content=b'{"question": "TVA \xe9t\xe9"}', headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_rate_limit_is_per_browser_not_per_shared_ip(api):
    client, _ = api(rate_limit_client_per_minute=2)
    alice = {"X-Client-Id": "alice-0000-browser"}

    for _ in range(2):
        assert client.post("/api/v1/answers", json=QUESTION, headers=alice).status_code == 200
    blocked = client.post("/api/v1/answers", json=QUESTION, headers=alice)
    other_browser = client.post("/api/v1/answers", json=QUESTION, headers={"X-Client-Id": "bob-0000-browser"})

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert int(blocked.headers["Retry-After"]) >= 1
    assert other_browser.status_code == 200


def test_daily_budget_caps_llm_spending(api):
    client, _ = api(daily_answer_budget=1)

    assert client.post("/api/v1/answers", json=QUESTION).status_code == 200
    response = client.post("/api/v1/answers", json=QUESTION, headers={"X-Client-Id": "another-browser"})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "DAILY_QUOTA_EXCEEDED"


def test_llm_outage_returns_503_and_is_traced(api):
    client, services = api(llm=ScriptedLLM([LLMUnavailableError("délai dépassé")]))

    response = client.post("/api/v1/answers", json=QUESTION)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_UNAVAILABLE"
    assert services.traces.traces[0].status == "error"


def test_unexpected_error_returns_500_in_the_error_format(api):
    client, _ = api(llm=ScriptedLLM([RuntimeError("panne")]), raise_server_exceptions=False)

    response = client.post("/api/v1/answers", json=QUESTION)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


def test_document_list_and_detail(api):
    client, _ = api()

    listing = client.get("/api/v1/documents").json()
    detail = client.get("/api/v1/documents/demo-cgi-2026")
    missing = client.get("/api/v1/documents/inconnu")

    assert listing["corpus_version"] == "demo"
    assert [doc["document_id"] for doc in listing["documents"]] == ["demo-cgi-2026"]
    assert detail.status_code == 200
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def _catalog(file_path):
    return InMemoryCatalog(
        [
            DocumentRecord(
                document_id="cgi-2026", title="CGI 2026", domain="fiscal", country="BJ",
                document_type="code_ou_loi", source_level=1, version="2026", status="en_vigueur",
                file_path=file_path, has_text_layer=True,
            )
        ]
    )


def test_original_pdf_is_served_inline(api, tmp_path: Path):
    (tmp_path / "Fiscal").mkdir()
    (tmp_path / "Fiscal" / "cgi.pdf").write_bytes(b"%PDF-1.7 test")
    client, _ = api(catalog=_catalog("Fiscal/cgi.pdf"), data_raw_dir=tmp_path)

    response = client.get("/api/v1/documents/cgi-2026/file")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")
    assert response.content == b"%PDF-1.7 test"


def test_files_outside_the_raw_directory_are_never_served(api, tmp_path: Path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (tmp_path / "secret.pdf").write_bytes(b"secret")
    client, _ = api(catalog=_catalog("../secret.pdf"), data_raw_dir=raw)

    response = client.get("/api/v1/documents/cgi-2026/file")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_FILE_NOT_FOUND"


def test_search_requires_the_admin_token_when_configured(api):
    client, _ = api(admin_token="secret-equipe")
    payload = {"query": "TVA taux", "filters": QUESTION["filters"], "limit": 5}

    refused = client.post("/api/v1/search", json=payload)
    allowed = client.post("/api/v1/search", json=payload, headers={"X-Admin-Token": "secret-equipe"})

    assert refused.status_code == 401
    assert allowed.status_code == 200
    assert allowed.json()["results"][0]["chunk_id"] == "demo-cgi-2026:0"


def test_feedback_is_stored(api):
    client, services = api()

    response = client.post("/api/v1/feedback", json={"request_id": "abc", "rating": "down", "comment": "Faux"})

    assert response.status_code == 204
    assert services.feedback.entries == [("abc", -1, "Faux")]
    assert client.post("/api/v1/feedback", json={"request_id": "abc", "rating": "bof"}).status_code == 422


def test_health(api):
    client, _ = api()

    body = client.get("/api/health").json()

    assert body == {
        "status": "ok", "version": "0.1.0", "engine": "fake", "database": "not_configured",
        "corpus_version": "demo",
    }


def test_published_contract_is_up_to_date():
    assert OPENAPI_PATH.read_text(encoding="utf-8") == render_openapi(), (
        "docs/api/openapi.json est périmé : lancer python scripts/export_openapi.py"
    )
