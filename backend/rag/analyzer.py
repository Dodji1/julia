"""Analyse de la question. V0 : règles simples, sans appel au LLM."""

from __future__ import annotations

import re

from backend.rag.types import AnalyzedQuery
from contracts import article_key

_ARTICLE = re.compile(
    r"\bart(?:icle)?s?\.?\s*"
    r"(\d{1,4}(?:\s*-\s*\d{1,3})?"
    r"(?:\s+(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies))?)\b",
    re.IGNORECASE,
)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


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
    )
