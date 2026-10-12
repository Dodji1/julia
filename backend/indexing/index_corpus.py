"""Commande d'indexation.

Exemples :
    python -m backend.indexing --chunks "data/processed/chunks/*.jsonl" --dry-run
    python -m backend.indexing --chunks "data/processed/chunks/*.jsonl"
    python -m backend.indexing --chunks "data/processed/chunks/*.jsonl" --prune

Sémantique : chaque document présent dans les JSONL est remplacé en entier ; les autres documents
déjà indexés sont conservés, sauf avec `--prune`. Tout est écrit dans une seule transaction.
"""

from __future__ import annotations

import argparse
import glob
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

import numpy as np
import psycopg
from pydantic import ValidationError

from backend.db import EMBEDDING_DIMENSION
from backend.indexing.manifest import Manifest, load_manifest
from backend.rag.interfaces import Embedder
from contracts import LegalChunk

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST = Path("data/metadata/corpus_manifest.yaml")


class IndexingError(ValueError):
    def __init__(self, errors: Sequence[str]) -> None:
        super().__init__(f"{len(errors)} erreur(s) :\n" + "\n".join(f"  - {error}" for error in errors))
        self.errors = list(errors)


@dataclass(frozen=True, slots=True)
class IndexReport:
    corpus_version: str
    documents: int
    chunks: int
    pruned_documents: int


def read_chunks(paths: Iterable[Path]) -> list[LegalChunk]:
    chunks: list[LegalChunk] = []
    errors: list[str] = []
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                chunks.append(LegalChunk.model_validate_json(line))
            except ValidationError as error:
                for detail in error.errors():
                    field = ".".join(str(part) for part in detail["loc"]) or "ligne"
                    errors.append(f"{path.name}:{line_number} : {field} — {detail['msg']}")
    if errors:
        raise IndexingError(errors)
    return chunks


def check_against_manifest(chunks: Sequence[LegalChunk], manifest: Manifest) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_positions: set[tuple[str, int]] = set()
    titles: dict[str, str] = {}
    for chunk in chunks:
        if chunk.chunk_id in seen_ids:
            errors.append(f"{chunk.chunk_id} : chunk_id en double")
        seen_ids.add(chunk.chunk_id)
        if (chunk.document_id, chunk.ordinal) in seen_positions:
            errors.append(f"{chunk.chunk_id} : ordinal {chunk.ordinal} déjà utilisé dans {chunk.document_id}")
        seen_positions.add((chunk.document_id, chunk.ordinal))

        entry = manifest.entries.get(chunk.document_id)
        if entry is None:
            errors.append(f"{chunk.chunk_id} : document_id « {chunk.document_id} » absent du manifeste")
            continue
        if entry.duplicate_of:
            errors.append(f"{chunk.chunk_id} : {chunk.document_id} est un doublon de {entry.duplicate_of}")
        for field in ("status", "source_level", "country", "document_type"):
            actual, expected = _plain(getattr(chunk, field)), _plain(getattr(entry, field))
            if actual != expected:
                errors.append(f"{chunk.chunk_id} : {field} = {actual!r}, le manifeste indique {expected!r}")
        first_title = titles.setdefault(chunk.document_id, chunk.document_title)
        if chunk.document_title != first_title:
            errors.append(f"{chunk.chunk_id} : document_title différent des autres chunks du document")
    return errors


def _plain(value: object) -> object:
    return value.value if isinstance(value, Enum) else value


def embedding_text(chunk: LegalChunk) -> str:
    """Texte vectorisé : le contenu précédé de son contexte (document, emplacement, article)."""
    header = " — ".join(
        part
        for part in (chunk.document_title, chunk.location, f"Article {chunk.article}" if chunk.article else None)
        if part
    )
    return f"{header}\n{chunk.content}"


def index_corpus(
    conn: psycopg.Connection,
    chunks: Sequence[LegalChunk],
    manifest: Manifest,
    embedder: Embedder,
    *,
    corpus_version: str,
    prune: bool = False,
) -> IndexReport:
    if embedder.dimension != EMBEDDING_DIMENSION:
        raise IndexingError(
            [f"le modèle {embedder.model_name} produit {embedder.dimension} dimensions, la base en attend "
             f"{EMBEDDING_DIMENSION} : il faut une migration"]
        )
    errors = check_against_manifest(chunks, manifest)
    if errors:
        raise IndexingError(errors)
    if not chunks:
        raise IndexingError(["aucun chunk à indexer"])

    logger.info("Calcul de %d embeddings avec %s…", len(chunks), embedder.model_name)
    vectors = embedder.embed_documents([embedding_text(chunk) for chunk in chunks])

    first_chunk = {}
    for chunk in chunks:
        first_chunk.setdefault(chunk.document_id, chunk)
    document_ids = sorted(first_chunk)

    with conn.transaction(), conn.cursor() as cursor:
        cursor.executemany(_UPSERT_DOCUMENT, [_document_row(first_chunk[i], manifest) for i in document_ids])
        cursor.execute("DELETE FROM chunks WHERE document_id = ANY(%s)", (document_ids,))
        pruned = 0
        if prune:
            cursor.execute("DELETE FROM documents WHERE NOT (document_id = ANY(%s))", (document_ids,))
            pruned = cursor.rowcount
        cursor.executemany(_INSERT_CHUNK, [_chunk_row(chunk) for chunk in chunks])
        cursor.executemany(
            "INSERT INTO chunk_embeddings (chunk_id, model, embedding) VALUES (%s, %s, %s)",
            [
                (chunk.chunk_id, embedder.model_name, np.asarray(vector, dtype=np.float32))
                for chunk, vector in zip(chunks, vectors, strict=True)
            ],
        )
        total_documents, total_chunks = cursor.execute(
            "SELECT (SELECT count(*) FROM documents), (SELECT count(*) FROM chunks)"
        ).fetchone()
        cursor.execute(
            "INSERT INTO corpus_versions (corpus_version, embedding_model, documents, chunks)"
            " VALUES (%s, %s, %s, %s)",
            (corpus_version, embedder.model_name, total_documents, total_chunks),
        )
    return IndexReport(corpus_version, len(document_ids), len(chunks), pruned)


_UPSERT_DOCUMENT = """
INSERT INTO documents (document_id, title, domain, country, organization, document_type, source_level,
                       version_label, status, file_path, sha256, has_text_layer, in_mvp, indexed_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (document_id) DO UPDATE SET
    title = EXCLUDED.title, domain = EXCLUDED.domain, country = EXCLUDED.country,
    organization = EXCLUDED.organization, document_type = EXCLUDED.document_type,
    source_level = EXCLUDED.source_level, version_label = EXCLUDED.version_label,
    status = EXCLUDED.status, file_path = EXCLUDED.file_path, sha256 = EXCLUDED.sha256,
    has_text_layer = EXCLUDED.has_text_layer, in_mvp = EXCLUDED.in_mvp, indexed_at = now()
"""

_INSERT_CHUNK = """
INSERT INTO chunks (chunk_id, document_id, ordinal, title, chapter, section, location, article,
                    article_key, paragraph, page_start, page_end, content, tags, is_ocr)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def _document_row(chunk: LegalChunk, manifest: Manifest) -> tuple:
    entry = manifest.entries[chunk.document_id]
    return (
        entry.id,
        chunk.document_title,
        entry.domain,
        entry.country,
        entry.organization or None,
        entry.document_type,
        entry.source_level,
        chunk.version or entry.version_label,
        entry.status.value,
        manifest.file_path(entry),
        entry.sha256,
        entry.has_text_layer,
        entry.in_mvp,
    )


def _chunk_row(chunk: LegalChunk) -> tuple:
    return (
        chunk.chunk_id,
        chunk.document_id,
        chunk.ordinal,
        chunk.title,
        chunk.chapter,
        chunk.section,
        chunk.location,
        chunk.article,
        chunk.article_key,
        chunk.paragraph,
        chunk.page_start,
        chunk.page_end,
        chunk.content,
        chunk.tags,
        chunk.is_ocr,
    )


def expand_paths(patterns: Sequence[str]) -> list[Path]:
    """Développe les motifs (PowerShell ne le fait pas)."""
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern)) if any(char in pattern for char in "*?[") else [pattern]
        paths.extend(Path(match) for match in matches)
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.indexing", description=__doc__.splitlines()[0])
    parser.add_argument("--chunks", nargs="+", required=True, help="fichiers ou motifs JSONL LegalChunk")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--corpus-version", default=datetime.now(UTC).strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--prune", action="store_true", help="supprimer les documents absents des JSONL")
    parser.add_argument("--dry-run", action="store_true", help="valider sans calculer ni écrire")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    paths = expand_paths(args.chunks)
    if not paths:
        logger.error("Aucun fichier ne correspond à %s", " ".join(args.chunks))
        return 1
    manifest = load_manifest(args.manifest)
    try:
        chunks = read_chunks(paths)
        errors = check_against_manifest(chunks, manifest)
        if errors:
            raise IndexingError(errors)
    except IndexingError as error:
        logger.error("Fichiers non conformes au contrat LegalChunk — %s", error)
        return 1

    documents = len({chunk.document_id for chunk in chunks})
    if args.dry_run:
        logger.info("Validation réussie : %d chunks, %d documents, %d fichiers.", len(chunks), documents, len(paths))
        return 0

    from backend.app.config import Settings
    from backend.db.migrate import migrate
    from backend.rag.models import build_embedder
    from pgvector.psycopg import register_vector

    settings = Settings()
    if not settings.database_url:
        logger.error("JULIA_DATABASE_URL n'est pas défini.")
        return 1
    migrate(settings.database_url)
    embedder = build_embedder(settings.embedding_model, device=settings.model_device)
    with psycopg.connect(settings.database_url) as conn:
        register_vector(conn)
        report = index_corpus(
            conn, chunks, manifest, embedder, corpus_version=args.corpus_version, prune=args.prune
        )
    logger.info(
        "Corpus %s indexé : %d documents, %d chunks%s.",
        report.corpus_version,
        report.documents,
        report.chunks,
        f", {report.pruned_documents} documents retirés" if args.prune else "",
    )
    return 0
