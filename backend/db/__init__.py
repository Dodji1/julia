"""Accès PostgreSQL + pgvector : schéma, recherche hybride, catalogue, traces."""

EMBEDDING_DIMENSION = 1024
"""Doit correspondre à `vector(1024)` dans `migrations/001_init.sql` (BGE-M3)."""
