"""Lecture du manifeste du corpus (`data/metadata/corpus_manifest.yaml`)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from contracts import DocumentStatus


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    path: str
    title: str
    domain: str
    country: str
    organization: str | None = None
    document_type: str
    source_level: int
    version_label: str | None = None
    status: DocumentStatus
    has_text_layer: bool
    in_mvp: bool = False
    sha256: str | None = None
    duplicate_of: str | None = None


@dataclass(frozen=True, slots=True)
class Manifest:
    source_root: str
    entries: dict[str, ManifestEntry]

    def file_path(self, entry: ManifestEntry) -> str:
        """Chemin du PDF relatif à `data/raw/`."""
        return f"{self.source_root}/{entry.path}" if self.source_root else entry.path


def load_manifest(path: Path) -> Manifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = [ManifestEntry.model_validate(entry) for entry in raw.get("entries", [])]
    return Manifest(source_root=raw.get("source_root") or "", entries={entry.id: entry for entry in entries})
