from typing import Literal, Optional
from enum import StrEnum
from pydantic import BaseModel, Field

class DocumentStatus(StrEnum):
    EN_VIGUEUR = "en_vigueur"
    ARCHIVE = "archive"
    A_VERIFIER = "a_verifier"


class LegalChunk(BaseModel):

    chunk_id: str

    document_id: str

    ordinal: int

    content: str

    source_level: int

    country: Literal[
        "BJ",
        "OHADA",
        "CEDEAO"
    ]

    document_type: str

    document_title: str

    status: Literal[
        "en_vigueur",
        "archive",
        "a_verifier"
    ]

    version: Optional[str] = None

    title: Optional[str] = None

    chapter: Optional[str] = None

    section: Optional[str] = None

    article: Optional[str] = None

    page_start: Optional[int] = None

    page_end: Optional[int] = None

    is_ocr: bool = False

    tags: list[str] = Field(
        default_factory=list
    )

    def normalize_tags(self):

        self.tags = sorted(
            {
                tag.strip().upper()
                for tag in self.tags
                if tag and tag.strip()
            }
        )

        return self