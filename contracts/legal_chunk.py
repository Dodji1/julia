"""Modèle canonique `LegalChunk` (issue #12).

C'est la sortie officielle du découpage juridique (`06_chunk_documents.py`) et l'entrée unique de
l'indexation. Le pipeline écrit un fichier JSONL par document, une ligne = un `LegalChunk`.

Les champs documentaires (statut, niveau de source, type, pays) doivent être identiques à ceux du
manifeste `data/metadata/corpus_manifest.yaml` : l'indexation refuse un chunk qui les contredit.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DocumentStatus(StrEnum):
    EN_VIGUEUR = "en_vigueur"
    ARCHIVE = "archive"
    A_VERIFIER = "a_verifier"


_WHITESPACE = re.compile(r"\s+")


def article_key(article: str | None) -> str | None:
    """Forme normalisée d'un numéro d'article, utilisée pour la recherche exacte.

    « Art. 1085  Ter » et « 1085 ter » donnent « 1085 ter » ; « 12 - 1 » donne « 12-1 » ;
    « 1er » et « premier » donnent « 1 ».
    """
    if article is None:
        return None
    key = _WHITESPACE.sub(" ", article).strip().lower()
    key = re.sub(r"^(article|art\.?)\s*", "", key)
    key = re.sub(r"^(1\s*er|premier)\b", "1", key)
    key = re.sub(r"\s*-\s*", "-", key)
    return key or None


class LegalChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    chunk_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{2,199}$")
    document_id: str = Field(min_length=1)
    ordinal: int = Field(ge=0, description="Position du chunk dans le document, à partir de 0.")
    content: str = Field(min_length=1)

    source_level: int = Field(ge=1, le=4)
    country: str = Field(min_length=2, description="Code du manifeste : BJ, OHADA, CEDEAO…")
    document_type: str = Field(min_length=1)
    document_title: str = Field(min_length=1)
    status: DocumentStatus
    version: str | None = None

    title: str | None = Field(default=None, description="Livre ou titre.")
    chapter: str | None = None
    section: str | None = None
    article: str | None = None
    paragraph: str | None = None

    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)

    is_ocr: bool = False
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, tags: list[str]) -> list[str]:
        normalized = [tag.strip().upper() for tag in tags if tag.strip()]
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def _check_pages(self) -> LegalChunk:
        if self.page_start and self.page_end and self.page_end < self.page_start:
            raise ValueError("page_end doit être supérieur ou égal à page_start")
        return self

    @property
    def article_key(self) -> str | None:
        return article_key(self.article)

    @property
    def location(self) -> str | None:
        """Chemin hiérarchique lisible : « Livre II › Chapitre III › Section II »."""
        parts = [part for part in (self.title, self.chapter, self.section) if part]
        return " › ".join(parts) or None
