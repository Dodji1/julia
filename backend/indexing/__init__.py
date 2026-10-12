"""Indexation : manifeste + fichiers JSONL `LegalChunk` → PostgreSQL (documents, chunks, embeddings).

C'est le point de jonction entre le pipeline d'ingestion (équipe RAG) et l'API : le pipeline produit
des JSONL conformes au contrat, cette commande les valide, calcule les embeddings avec le même modèle
que l'API et les charge.
"""
