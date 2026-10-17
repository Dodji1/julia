"""Découpage de guides et procédures qui ne sont pas structurés en articles.

Ce module complète legal_parser.py sans modifier sa définition d'un Article.
Il détecte seulement des marqueurs lisibles (Étape, Phase, Objet, I-, 1), A.)
et conserve les passages sans titre comme unités page-aware. Les titres en
capitales seuls ne sont pas interprétés automatiquement : cela évite de prendre
les en-têtes administratifs des scans pour des titres de section.
"""
import re
from typing import List, Optional

from models import Page, ProcedureSection
from normalizer import normalize_text


# Titres textuels qui apparaissent dans les notes et les guides.
_NAMED_HEADING_PATTERNS = [
    re.compile(r"^(?:ÉTAPE|ETAPE|PHASE)\b.{0,140}$", re.IGNORECASE),
    re.compile(r"^(?:OBJET|RÉFÉRENCES|REFERENCES|CONTEXTE|DÉFINITIONS|DEFINITIONS)\s*[:\-]?.{0,120}$", re.IGNORECASE),
]

# Marqueurs juridiques/alphabétiques numérotés avec ponctuation claire.
# Une lettre seule suivie d'un tiret n'est pas acceptée pour ne pas prendre
# « e-services » pour un titre.
_NUMBERED_HEADING_RE = re.compile(
    r"^(?P<marker>(?:(?:[IVX]+|\d+(?:\.\d+)*)(?:[.)\-:])|[A-Ha-h][.)]))\s*(?P<title>.+)$",
    re.IGNORECASE,
)


def _is_section_heading(line: str) -> bool:
    """Retourner True seulement si la ligne a un marqueur de structure clair."""
    value = " ".join(line.strip().split())
    if not value or len(value) > 150:
        return False
    if any(pattern.match(value) for pattern in _NAMED_HEADING_PATTERNS):
        return True

    match = _NUMBERED_HEADING_RE.match(value)
    if match is None:
        return False
    # Les marqueurs OCR isolés (ex. « 2022) : ») ne deviennent pas des titres.
    return sum(character.isalpha() for character in match.group("title")) >= 4


def _split_text(text: str, max_chars: int) -> List[str]:
    """Découper un passage trop long sur les espaces, sans supprimer de mots."""
    words = text.split()
    if not words:
        return [""]

    chunks = []
    current_words = []
    current_length = 0
    for word in words:
        added_length = len(word) + (1 if current_words else 0)
        if current_words and current_length + added_length > max_chars:
            chunks.append(" ".join(current_words))
            current_words = []
            current_length = 0
        current_words.append(word)
        current_length += len(word) + (1 if len(current_words) > 1 else 0)

    if current_words:
        chunks.append(" ".join(current_words))
    return chunks


def parse_procedural_pages(
    pages: List[Page],
    document_id: str,
    source_filename: str,
    max_chars: int = 1400,
) -> List[ProcedureSection]:
    """Transformer les pages en unités de procédure avec titre et pages source.

    Le parseur est appelé par le CLI uniquement lorsque legal_parser n'a trouvé
    aucun article. Chaque unité porte donc un type distinct et ne se fait jamais
    passer pour un Article. Les pages sans titre explicite restent découpées
    séparément pour garder des références de page précises.
    """
    groups = []
    current = None

    def start_group(title: Optional[str], page: Page):
        """Créer l'état temporaire d'une unité pendant le parcours du PDF."""
        return {
            "section_title": title,
            "lines": [],
            "page_start": page.page_number,
            "page_end": page.page_number,
            "extraction_methods": set(),
            "needs_human_review": False,
        }

    def flush_group():
        """Fermer l'unité courante avant d'en commencer une autre."""
        nonlocal current
        if current is not None:
            groups.append(current)
            current = None

    previous_page_number = None
    for page in pages:
        # Un passage sans titre ne traverse pas une frontière de page : la
        # citation page_start/page_end reste alors immédiatement exploitable.
        if (
            current is not None
            and current["section_title"] is None
            and previous_page_number is not None
            and page.page_number != previous_page_number
        ):
            flush_group()

        # Utiliser le normaliseur commun : espaces, fins de ligne et soft-hyphens.
        for raw_line in normalize_text(page.text).splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if _is_section_heading(line):
                flush_group()
                current = start_group(" ".join(line.split()), page)
            elif current is None:
                current = start_group(None, page)

            current["lines"].append(line)
            current["page_end"] = page.page_number
            current["extraction_methods"].add(page.extraction_method)
            current["needs_human_review"] |= page.needs_ocr_review

        previous_page_number = page.page_number
    flush_group()

    sections = []
    next_section_number = 1
    for group in groups:
        lines = list(group["lines"])
        # Le titre est conservé séparément, comme article_title dans Article.
        if group["section_title"] and lines and lines[0] == group["section_title"]:
            lines = lines[1:]
        body = "\n".join(lines).strip()

        # Un titre sans paragraphe après lui reste quand même indexable.
        if not body and group["section_title"]:
            body = group["section_title"]

        for part_index, text_part in enumerate(_split_text(body, max_chars), start=1):
            sections.append(ProcedureSection(
                section_id=(
                    f"{document_id}__procedure_{next_section_number:04d}"
                    f"_part_{part_index:02d}"
                ),
                document_id=document_id,
                source_filename=source_filename,
                unit_type="non_article_section",
                section_title=group["section_title"],
                text=text_part,
                page_start=group["page_start"],
                page_end=group["page_end"],
                part_index=part_index,
                extraction_methods=sorted(group["extraction_methods"]),
                needs_human_review=group["needs_human_review"],
            ))
        next_section_number += 1

    return sections
