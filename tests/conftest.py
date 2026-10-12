from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from backend.rag.types import Passage


def _make_passage(index: int = 1, **overrides: Any) -> Passage:
    fields: dict[str, Any] = {
        "chunk_id": f"cgi-2026:{index}",
        "document_id": "cgi-2026",
        "document_title": "Code général des impôts 2026",
        "content": f"Contenu exact du passage {index}.",
        "status": "en_vigueur",
        "source_level": 1,
        "document_type": "code_ou_loi",
        "version": "2026",
        "location": "Livre I › Chapitre II",
        "article": str(index),
        "page": index,
        "relevance": 0.8,
    }
    fields.update(overrides)
    return Passage(**fields)


@pytest.fixture
def make_passage() -> Callable[..., Passage]:
    return _make_passage


@pytest.fixture
def llm_json() -> Callable[[str, str], str]:
    def render(status: str, markdown: str) -> str:
        return json.dumps({"status": status, "answer_markdown": markdown}, ensure_ascii=False)

    return render
