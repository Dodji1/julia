"""Garde 2 : vérification et renumérotation des citations produites par le LLM.

Le LLM cite les passages par leur étiquette ([P3], [P1, P4]). On ne garde que les étiquettes qui
existent dans le contexte, puis on les renumérote [1], [2]… dans l'ordre de première apparition :
c'est le format attendu par l'interface. Les numéros nus ([1]) écrits par le modèle sont supprimés,
car ils ne renvoient à aucun passage vérifiable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.rag.types import Passage

_LABEL_GROUP = re.compile(r"([ \t]*)\[\s*(P\d+(?:\s*[,;]\s*P\d+)*)\s*\]", re.IGNORECASE)
_BARE_NUMBERS = re.compile(r"[ \t]*\[\s*\d+(?:\s*[,;]\s*\d+)*\s*\]")


@dataclass(frozen=True, slots=True)
class VerifiedAnswer:
    answer_markdown: str
    sources: tuple[Passage, ...]
    discarded: tuple[str, ...]


def verify_citations(answer_markdown: str, passages: dict[str, Passage]) -> VerifiedAnswer:
    order: list[str] = []
    discarded: list[str] = []

    def drop_bare(match: re.Match[str]) -> str:
        discarded.append(match.group(0).strip())
        return ""

    def renumber(match: re.Match[str]) -> str:
        numbers: list[str] = []
        for raw in re.split(r"[,;]", match.group(2)):
            label = raw.strip().upper()
            if label not in passages:
                discarded.append(label)
                continue
            if label not in order:
                order.append(label)
            token = f"[{order.index(label) + 1}]"
            if token not in numbers:
                numbers.append(token)
        return match.group(1) + "".join(numbers) if numbers else ""

    text = _BARE_NUMBERS.sub(drop_bare, answer_markdown)
    text = _LABEL_GROUP.sub(renumber, text)
    return VerifiedAnswer(
        answer_markdown=text.strip(),
        sources=tuple(passages[label] for label in order),
        discarded=tuple(discarded),
    )


def strip_citations(answer_markdown: str) -> str:
    """Retire toute référence, pour les messages qui ne s'appuient sur aucune source."""
    text = _BARE_NUMBERS.sub("", answer_markdown)
    return _LABEL_GROUP.sub("", text).strip()
