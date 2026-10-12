"""Recherche hybride dans PostgreSQL : vectorielle + plein texte + article exact, fusion RRF.

Les trois branches appliquent les mêmes filtres (domaine, pays applicables, statut). La fusion par
rangs réciproques (RRF, k = 60) évite d'avoir à calibrer ensemble des scores de nature différente.
`relevance` reste la similarité cosinus de la branche vectorielle : c'est elle que la garde 1 compare
au seuil.
"""

from __future__ import annotations

import numpy as np
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from backend.rag.interfaces import Embedder
from backend.rag.types import AnalyzedQuery, Passage, SearchFilters

APPLICABLE_COUNTRIES: dict[str, tuple[str, ...]] = {
    # Textes applicables au Bénin : droit national et droit communautaire.
    "BJ": ("BJ", "OHADA", "UEMOA", "CEDEAO"),
}

_FILTERS = """
    d.domain = %(domain)s
    AND d.country = ANY(%(countries)s)
    AND d.status = ANY(%(statuses)s)
"""

HYBRID_SQL = f"""
WITH
vec AS (
    SELECT e.chunk_id,
           1 - (e.embedding <=> %(embedding)s) AS similarity,
           row_number() OVER (ORDER BY e.embedding <=> %(embedding)s) AS rnk
    FROM chunk_embeddings e
    JOIN chunks c ON c.chunk_id = e.chunk_id
    JOIN documents d ON d.document_id = c.document_id
    WHERE e.model = %(model)s AND {_FILTERS}
    ORDER BY e.embedding <=> %(embedding)s
    LIMIT %(k)s
),
fts_query AS (
    -- plainto_tsquery combine les mots par ET : on passe en OU pour ne pas exiger tous les mots.
    SELECT CASE WHEN numnode(q) = 0 THEN NULL
                ELSE replace(q::text, ' & ', ' | ')::tsquery END AS q
    FROM plainto_tsquery('french_unaccent', %(text)s) AS q
),
fts AS (
    SELECT c.chunk_id,
           row_number() OVER (ORDER BY ts_rank_cd(c.content_tsv, fq.q) DESC) AS rnk
    FROM chunks c
    JOIN documents d ON d.document_id = c.document_id
    CROSS JOIN fts_query fq
    WHERE fq.q IS NOT NULL AND c.content_tsv @@ fq.q AND {_FILTERS}
    ORDER BY ts_rank_cd(c.content_tsv, fq.q) DESC
    LIMIT %(k)s
),
exact AS (
    SELECT c.chunk_id
    FROM chunks c
    JOIN documents d ON d.document_id = c.document_id
    WHERE c.article_key = ANY(%(articles)s) AND {_FILTERS}
    ORDER BY d.source_level, c.ordinal
    LIMIT %(k)s
),
fused AS (
    SELECT chunk_id,
           sum(score) AS rrf,
           max(similarity) AS similarity,
           bool_or(is_exact) AS is_exact
    FROM (
        SELECT chunk_id, 1.0 / (60 + rnk) AS score, similarity, false AS is_exact FROM vec
        UNION ALL
        SELECT chunk_id, 1.0 / (60 + rnk), NULL, false FROM fts
        UNION ALL
        SELECT chunk_id, 1.0 / 60, NULL, true FROM exact
    ) hits
    GROUP BY chunk_id
)
SELECT c.chunk_id, c.document_id, d.title AS document_title, c.content, d.status, d.source_level,
       d.document_type, d.version_label, c.location, c.article, c.page_start, c.is_ocr,
       f.similarity, f.is_exact
FROM fused f
JOIN chunks c ON c.chunk_id = f.chunk_id
JOIN documents d ON d.document_id = c.document_id
ORDER BY f.is_exact DESC, f.rrf DESC
LIMIT %(k)s
"""


class PgHybridRetriever:
    def __init__(self, pool: ConnectionPool, embedder: Embedder) -> None:
        self._pool = pool
        self._embedder = embedder

    def retrieve(self, query: AnalyzedQuery, filters: SearchFilters, limit: int) -> list[Passage]:
        statuses = ["en_vigueur", "a_verifier"] + (["archive"] if query.include_archived else [])
        params = {
            "embedding": np.asarray(self._embedder.embed_query(query.text), dtype=np.float32),
            "model": self._embedder.model_name,
            "text": query.text,
            "articles": list(query.article_keys),
            "domain": filters.domain,
            "countries": list(APPLICABLE_COUNTRIES.get(filters.jurisdiction, (filters.jurisdiction,))),
            "statuses": statuses,
            "k": limit,
        }
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
            rows = cursor.execute(HYBRID_SQL, params).fetchall()
        return [
            Passage(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                document_title=row["document_title"],
                content=row["content"],
                status=row["status"],
                source_level=row["source_level"],
                document_type=row["document_type"],
                version=row["version_label"],
                location=row["location"],
                article=row["article"],
                page=row["page_start"],
                is_ocr=row["is_ocr"],
                relevance=float(row["similarity"]) if row["similarity"] is not None else None,
                exact_match=row["is_exact"],
            )
            for row in rows
        ]
