import re
from collections import OrderedDict
from models import Article, LEVELS
from normalizer import normalize_text

# Generic legal hierarchy. Titles are usually placed on the next non-empty line.
LEVEL_PATTERNS = OrderedDict([
    ("livre", re.compile(r"^\s*LIVRE\s+([0-9IVXLCDM]+)\s*$", re.I)),
    ("partie", re.compile(r"^\s*PARTIE\s+([0-9IVXLCDM]+)\s*$", re.I)),
    ("titre", re.compile(r"^\s*TITRE\s+([0-9IVXLCDM]+)\s*$", re.I)),
    ("sous_titre", re.compile(r"^\s*SOUS[- ]?TITRE\s+([0-9IVXLCDM]+)\s*$", re.I)),
    ("chapitre", re.compile(r"^\s*CHAPITRE\s+([0-9IVXLCDM]+|PREMIER|SECOND|IIIe|IVe)\s*$", re.I)),
    ("section", re.compile(r"^\s*SECTION\s+([0-9IVXLCDM]+|PREMIERE|PREMIÈRE|DEUXIEME|DEUXIÈME)\s*$", re.I)),
    ("sous_section", re.compile(r"^\s*SOUS[- ]SECTION\s+([0-9IVXLCDM]+)\s*$", re.I)),
    ("paragraphe", re.compile(r"^\s*PARAGRAPHE\s+([0-9IVXLCDM]+)\s*$", re.I)),
    ("sous_paragraphe", re.compile(r"^\s*SOUS[- ]PARAGRAPHE\s+([0-9IVXLCDM]+)\s*$", re.I)),
])

ARTICLE_RE = re.compile(
    r"^\s*(?:ARTICLE|ART(?:ICLE)?\.?)\s*([0-9]+(?:\s*(?:ER|ÈR|ER\.))?|[IVXLCDM]+)\s*[:.\-]?\s*(.*)$",
    re.I
)

def _looks_like_title(line):
    if len(line) > 180: return False
    if ARTICLE_RE.match(line): return False
    return True

def parse_pages(pages, document_id):
    hierarchy = {}
    pending_level = None
    articles = []
    current = None

    def snapshot():
        return [
            {"level": k, "number": v["number"], "title": v["title"]}
            for k, v in hierarchy.items()
        ]

    def flush():
        nonlocal current
        if not current:
            return
        current["text"] = normalize_text("\n".join(current["text_lines"]))
        current.pop("text_lines", None)
        articles.append(Article(**current))
        current = None

    for page in pages:
        lines = page.text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Hierarchy marker
            found = False
            for level, pattern in LEVEL_PATTERNS.items():
                if "article" in line.lower():
                    print(
                        f"ARTICLE FOUND > {line}"
                    )
                m = pattern.match(line)

                if "article" in line.lower():

                    print(
                        f"ARTICLE FOUND > {line}"
                    )

                if m:
                    pending_level = (level, m.group(1).strip())
                    found = True
                    break
            if found:
                i += 1
                continue

            # Pending marker: next meaningful line is its title.
            if pending_level:
                level, number = pending_level
                hierarchy[level] = {"number": number, "title": line}
                # Remove deeper levels after a new parent.
                idx = LEVELS.index(level)
                for deeper in LEVELS[idx+1:]:
                    hierarchy.pop(deeper, None)
                pending_level = None
                i += 1
                continue

            # Article start
            m = ARTICLE_RE.match(line)
            if m:
                flush()
                number = m.group(1).replace(" ", "").rstrip(".").lower()
                title = m.group(2).strip() or None
                current = {
                    "article_id": f"{document_id}__article_{number}",
                    "document_id": document_id,
                    "article_number": number,
                    "article_title": title,
                    "hierarchy": snapshot(),
                    "text_lines": [line],
                    "page_start": page.page_number,
                    "page_end": page.page_number,
                }
                i += 1
                continue

            if current:
                current["text_lines"].append(line)
                current["page_end"] = page.page_number
            i += 1

    flush()
    return articles, list(hierarchy.values())
