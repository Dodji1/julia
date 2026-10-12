import json
from pathlib import Path

import pytest

from backend.indexing.index_corpus import (
    IndexingError,
    check_against_manifest,
    embedding_text,
    main,
    read_chunks,
)
from backend.indexing.manifest import load_manifest
from contracts import LegalChunk

REAL_MANIFEST = Path(__file__).resolve().parents[2] / "data" / "metadata" / "corpus_manifest.yaml"

MANIFEST_YAML = """
source_root: ressources
entries:
- id: cgi-2026
  path: Fiscal/CODE/cgi-2026.pdf
  title: cgi 2026
  domain: fiscal
  country: BJ
  document_type: code_ou_loi
  source_level: 1
  version_label: 2026 (LF 2025-22)
  status: en_vigueur
  has_text_layer: true
  in_mvp: true
  sha256: abc
- id: note-copie
  path: Fiscal/note-copie.pdf
  title: note copie
  domain: fiscal
  country: BJ
  document_type: note_circulaire
  source_level: 2
  status: en_vigueur
  has_text_layer: false
  duplicate_of: note
"""


def chunk(**overrides):
    fields = {
        "chunk_id": "cgi-2026:art-1",
        "document_id": "cgi-2026",
        "ordinal": 0,
        "content": "Texte de l'article premier.",
        "source_level": 1,
        "country": "BJ",
        "document_type": "code_ou_loi",
        "document_title": "Code général des impôts",
        "status": "en_vigueur",
        "article": "1",
        "title": "Livre I",
    }
    fields.update(overrides)
    return LegalChunk.model_validate(fields)


@pytest.fixture
def manifest(tmp_path):
    path = tmp_path / "manifest.yaml"
    path.write_text(MANIFEST_YAML, encoding="utf-8")
    return load_manifest(path)


def test_real_manifest_loads():
    manifest = load_manifest(REAL_MANIFEST)

    assert len(manifest.entries) == 48
    assert sum(entry.in_mvp for entry in manifest.entries.values()) == 33


def test_manifest_builds_the_path_under_data_raw(manifest):
    assert manifest.file_path(manifest.entries["cgi-2026"]) == "ressources/Fiscal/CODE/cgi-2026.pdf"


def test_consistent_chunks_pass(manifest):
    assert check_against_manifest([chunk(), chunk(chunk_id="cgi-2026:art-2", ordinal=1)], manifest) == []


def test_manifest_checks_report_every_problem(manifest):
    errors = check_against_manifest(
        [
            chunk(),
            chunk(ordinal=1),
            chunk(chunk_id="cgi-2026:art-3", ordinal=2, status="archive", source_level=2),
            chunk(chunk_id="inconnu:1", document_id="inconnu"),
            chunk(chunk_id="copie:1", document_id="note-copie", source_level=2, document_type="note_circulaire"),
        ],
        manifest,
    )

    joined = "\n".join(errors)
    assert "chunk_id en double" in joined
    assert "status = 'archive', le manifeste indique 'en_vigueur'" in joined
    assert "source_level = 2" in joined
    assert "absent du manifeste" in joined
    assert "doublon de note" in joined


def test_read_chunks_reports_file_and_line(tmp_path):
    path = tmp_path / "cgi.jsonl"
    path.write_text(chunk().model_dump_json() + "\n\n" + json.dumps({"chunk_id": "x"}) + "\n", encoding="utf-8")

    with pytest.raises(IndexingError) as error:
        read_chunks([path])

    assert any(message.startswith("cgi.jsonl:3 : ") for message in error.value.errors)


def test_embedding_text_carries_the_legal_context():
    text = embedding_text(chunk())

    assert text.splitlines()[0] == "Code général des impôts — Livre I — Article 1"
    assert text.endswith("Texte de l'article premier.")


def test_dry_run_validates_without_a_database(tmp_path, manifest, monkeypatch):
    manifest_path = tmp_path / "manifest.yaml"
    good = tmp_path / "good.jsonl"
    good.write_text(chunk().model_dump_json() + "\n", encoding="utf-8")
    bad = tmp_path / "bad.jsonl"
    bad.write_text(chunk(status="archive").model_dump_json() + "\n", encoding="utf-8")
    monkeypatch.delenv("JULIA_DATABASE_URL", raising=False)

    assert main(["--chunks", str(tmp_path / "good*.jsonl"), "--manifest", str(manifest_path), "--dry-run"]) == 0
    assert main(["--chunks", str(bad), "--manifest", str(manifest_path), "--dry-run"]) == 1
