from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from backend.stores import DocumentRecord

_DOCUMENTS_SQL = """
SELECT d.document_id, d.title, d.domain, d.country, d.document_type, d.source_level,
       d.version_label, d.status, d.file_path, d.has_text_layer, count(c.chunk_id) AS chunk_count
FROM documents d
LEFT JOIN chunks c ON c.document_id = d.document_id
{where}
GROUP BY d.document_id
ORDER BY d.source_level, d.title
"""


class PgCatalog:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def list_documents(self) -> list[DocumentRecord]:
        return [_record(row) for row in self._fetch(_DOCUMENTS_SQL.format(where=""), {})]

    def get_document(self, document_id: str) -> DocumentRecord | None:
        rows = self._fetch(_DOCUMENTS_SQL.format(where="WHERE d.document_id = %(id)s"), {"id": document_id})
        return _record(rows[0]) if rows else None

    def corpus_version(self) -> str | None:
        rows = self._fetch(
            "SELECT corpus_version FROM corpus_versions ORDER BY created_at DESC LIMIT 1", {}
        )
        return rows[0]["corpus_version"] if rows else None

    def _fetch(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
            return cursor.execute(sql, params).fetchall()


def _record(row: dict[str, Any]) -> DocumentRecord:
    return DocumentRecord(
        document_id=row["document_id"],
        title=row["title"],
        domain=row["domain"],
        country=row["country"],
        document_type=row["document_type"],
        source_level=row["source_level"],
        version=row["version_label"],
        status=row["status"],
        file_path=row["file_path"],
        has_text_layer=row["has_text_layer"],
        chunk_count=row["chunk_count"],
    )
