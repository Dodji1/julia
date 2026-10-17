"""Contrôles de qualité des chunks.

Ils ne bloquent pas l'indexation, contrairement aux contrôles du contrat : ils signalent ce que le
pipeline doit corriger pour que la recherche et les citations soient bonnes.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from backend.indexing.manifest import Manifest
from contracts import LegalChunk

LONG_CHUNK_CHARS = 4000
"""Au-delà, le chunk dilue la recherche et doit être redécoupé (par alinéa par exemple)."""
SHORT_CHUNK_CHARS = 60
"""En deçà, le chunk ne contient en général qu'un titre (« Article 5 ») sans le texte."""

_PLAUSIBLE_ARTICLE = re.compile(r"^\d")


@dataclass(frozen=True, slots=True)
class QualityCheck:
    code: str
    description: str
    items: list[str]


def quality_report(chunks: Sequence[LegalChunk], manifest: Manifest) -> list[QualityCheck]:
    by_document: dict[str, list[LegalChunk]] = defaultdict(list)
    for chunk in chunks:
        by_document[chunk.document_id].append(chunk)

    checks = [
        QualityCheck(
            "documents_mvp_absents",
            "documents du périmètre MVP sans aucun chunk",
            sorted(
                entry.id
                for entry in manifest.entries.values()
                if entry.in_mvp and not entry.duplicate_of and entry.id not in by_document
            ),
        ),
        QualityCheck(
            "trop_long",
            f"chunks de plus de {LONG_CHUNK_CHARS} caractères, à redécouper",
            [f"{c.chunk_id} ({len(c.content)} car.)" for c in sorted(chunks, key=lambda c: -len(c.content))
             if len(c.content) > LONG_CHUNK_CHARS],
        ),
        QualityCheck(
            "trop_court",
            f"chunks de moins de {SHORT_CHUNK_CHARS} caractères (titre seul ?), à fusionner avec le texte suivant",
            [f"{c.chunk_id} : « {c.content.strip()[:40]} »" for c in chunks
             if len(c.content.strip()) < SHORT_CHUNK_CHARS],
        ),
        QualityCheck(
            "ocr_incoherent",
            "is_ocr vaut true alors que le manifeste indique une couche texte "
            "(l'interface affichera « vérifier sur l'original » sur chaque citation)",
            [f"{document_id} ({sum(c.is_ocr for c in group)}/{len(group)} chunks)"
             for document_id, group in sorted(by_document.items())
             if manifest.entries[document_id].has_text_layer and any(c.is_ocr for c in group)],
        ),
        QualityCheck(
            "article_suspect",
            "numéro d'article qui ne commence pas par un chiffre (erreur de détection ?)",
            [f"{c.chunk_id} : article « {c.article} »" for c in chunks
             if c.article and not _PLAUSIBLE_ARTICLE.match(c.article_key or "")],
        ),
        QualityCheck(
            "hierarchie_suspecte",
            "title, chapter ou section reprend le début du texte au lieu d'un intitulé (Livre, Titre…)",
            [f"{c.chunk_id} : « {heading[:50]} »" for c in chunks
             for heading in (c.title, c.chapter, c.section)
             if heading and len(heading) > 60 and heading[:40] in c.content[:400]],
        ),
        QualityCheck(
            "doublon_dans_document",
            "même texte répété dans un document (en-têtes ou pieds de page ?)",
            [f"{document_id} : {count} fois « {content.strip()[:40]} »"
             for document_id, group in sorted(by_document.items())
             for content, count in Counter(c.content for c in group).items() if count > 1],
        ),
    ]
    return [check for check in checks if check.items]
