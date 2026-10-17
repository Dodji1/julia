import re
import unicodedata

def clean_line(line: str) -> str:
    line = line.replace("\u00ad", "")
    line = re.sub(r"[ \t]+", " ", line)
    return line.strip()

def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [clean_line(x) for x in text.split("\n")]
    lines = [x for x in lines if x]
    return "\n".join(lines)

def slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value or "document"
