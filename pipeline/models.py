from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

LEVELS = [
    "livre", "partie", "titre", "sous_titre", "chapitre",
    "section", "sous_section", "paragraphe", "sous_paragraphe",
    "annexe"
]

@dataclass
class Page:
    document_id: str
    page_number: int
    text: str
    char_count: int
    needs_ocr_review: bool
    extraction_method: str = "native"
    


@dataclass
class Article:
    article_id: str
    document_id: str
    article_number: str
    article_title: Optional[str]
    hierarchy: List[Dict[str, Any]]
    text: str
    page_start: int
    page_end: int

def to_dict(obj):
    return asdict(obj)

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcedureSection:
    section_id: str
    document_id: str

    source_filename: str

    unit_type: str

    section_title: Optional[str]

    text: str

    page_start: int
    page_end: int

    part_index: int

    extraction_methods: list[str]

    needs_human_review: bool
