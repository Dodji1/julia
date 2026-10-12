"""Contrats de données partagés entre le pipeline d'ingestion et le backend."""

from contracts.legal_chunk import DocumentStatus, LegalChunk, article_key

__all__ = ["DocumentStatus", "LegalChunk", "article_key"]
