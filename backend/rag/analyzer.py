"""Analyse de la question. V0 : règles simples, sans appel au LLM."""

from __future__ import annotations

import re

from backend.rag.types import AnalyzedQuery
from contracts import article_key

_ARTICLE = re.compile(
    r"\bart(?:icle)?s?\.?\s*"
    r"(premier|\d{1,4}(?:er)?(?:\s*-\s*\d{1,3})?"
    r"(?:\s+(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies))?)\b",
    re.IGNORECASE,
)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

# Textes que l'on peut nommer dans une question → motif sur l'identifiant du manifeste.
_DOCUMENT_HINTS = [
    (re.compile(r"\bcgi\b|code\s+g[ée]n[ée]ral\s+des\s+imp[ôo]ts", re.IGNORECASE), "%code-general-des-impots%"),
    (re.compile(r"code\s+des\s+investissements", re.IGNORECASE), "%code-des-investissements%"),
]


def analyze(question: str, reference_year: int) -> AnalyzedQuery:
    """Repère les articles cités et les années.

    Une année antérieure à `reference_year` (année du CGI en vigueur) fait inclure les textes
    archivés : « Quel était le taux en 2024 ? » doit pouvoir s'appuyer sur le CGI 2025.
    """
    text = " ".join(question.split())
    articles = tuple(
        dict.fromkeys(key for match in _ARTICLE.finditer(text) if (key := article_key(match.group(1))))
    )
    years = tuple(sorted({int(year) for year in _YEAR.findall(text)}))
    return AnalyzedQuery(
        text=text,
        article_keys=articles,
        years=years,
        include_archived=any(year < reference_year for year in years),
        document_patterns=tuple(pattern for regex, pattern in _DOCUMENT_HINTS if regex.search(text)),
    )
