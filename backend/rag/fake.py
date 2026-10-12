"""Composants factices : mode `JULIA_ENGINE=fake` et tests.

Les passages de démonstration ne contiennent aucune règle fiscale : ils servent uniquement à
exercer l'interface et le contrat d'API avant que le corpus réel soit indexé.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Sequence

from backend.rag.types import AnalyzedQuery, LLMCompletion, Passage, SearchFilters
from contracts import article_key

_STOPWORDS = {
    "les", "des", "une", "est", "sont", "quel", "quelle", "quels", "quelles", "pour", "sur",
    "dans", "par", "que", "qui", "aux", "avec", "comment", "elle", "ils", "mon", "mes", "son",
    "ses", "leur", "leurs", "cette", "ces", "faut", "doit", "peut",
}


def tokenize(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    return [token for token in re.findall(r"[a-z0-9]+", folded) if len(token) > 2 and token not in _STOPWORDS]


class InMemoryRetriever:
    """Score = part des mots de la question présents dans le passage."""

    def __init__(self, passages: Sequence[Passage]) -> None:
        self._passages = list(passages)

    def retrieve(self, query: AnalyzedQuery, filters: SearchFilters, limit: int) -> list[Passage]:
        question_tokens = set(tokenize(query.text))
        results: list[Passage] = []
        for passage in self._passages:
            if passage.status == "archive" and not query.include_archived:
                continue
            exact = passage.article is not None and article_key(passage.article) in query.article_keys
            overlap = len(question_tokens & set(tokenize(passage.content))) / max(len(question_tokens), 1)
            if exact or overlap > 0:
                results.append(dataclasses.replace(passage, relevance=round(overlap, 4), exact_match=exact))
        results.sort(key=lambda passage: (passage.exact_match, passage.relevance or 0.0), reverse=True)
        return results[:limit]


class ScriptedLLM:
    """Renvoie des réponses préparées, dans l'ordre ; enregistre les appels."""

    def __init__(self, responses: Sequence[str | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str) -> LLMCompletion:
        self.calls.append((system, user))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return LLMCompletion(text=response, model="scripted", input_tokens=100, output_tokens=50)


class DemoLLM:
    """Réponse de démonstration qui cite le premier passage, pour tester l'interface en mode live."""

    def complete_json(self, system: str, user: str) -> LLMCompletion:
        answer = (
            "**Mode démonstration : le moteur RAG réel n'est pas encore branché.**\n\n"
            "**Réponse**\nCette réponse illustre le format attendu : chaque affirmation renvoie "
            "au passage qui la fonde [P1].\n\n"
            "**Points d'attention**\nAucune règle fiscale n'est simulée dans ce mode."
        )
        return LLMCompletion(text=json.dumps({"status": "answered", "answer_markdown": answer}), model="demo")


class HashingEmbedder:
    """Embeddings déterministes par hachage des mots : tests d'intégration sans PyTorch."""

    def __init__(self, dimension: int = 1024, model_name: str = "test/hashing") -> None:
        self.dimension = dimension
        self.model_name = model_name

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in tokenize(text):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            vector[int.from_bytes(digest, "big") % self.dimension] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def demo_passages() -> list[Passage]:
    common = {
        "document_id": "demo-cgi-2026",
        "document_title": "Code général des impôts du Bénin 2026 (démonstration)",
        "status": "en_vigueur",
        "source_level": 1,
        "document_type": "code_ou_loi",
        "version": "2026",
    }
    return [
        Passage(
            chunk_id="demo-cgi-2026:0",
            content=(
                "Passage de démonstration sur la TVA, l'impôt sur les sociétés, les taux, les "
                "déclarations et les obligations des entreprises. Le texte exact de l'article sera "
                "relu dans la base documentaire une fois le corpus indexé."
            ),
            location="Démonstration",
            article="1",
            page=1,
            **common,
        ),
        Passage(
            chunk_id="demo-cgi-2026:1",
            content=(
                "Second passage de démonstration : procédures, contrôle fiscal, pénalités et "
                "recours. Aucune règle fiscale réelle n'est reproduite ici."
            ),
            location="Démonstration",
            article="2",
            page=2,
            **common,
        ),
    ]
