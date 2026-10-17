"""Modèles locaux : embeddings (BGE-M3) et reranking.

`sentence-transformers` (et donc PyTorch) n'est importé qu'à la construction, pour que l'API en
mode `fake` et les tests tournent sans les dépendances lourdes de `requirements-ml.txt`.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

from backend.rag.interfaces import Embedder
from backend.rag.types import Passage

HASHING_MODEL = "test/hashing"
"""Embeddings par hachage, sans PyTorch : pour développer sans installer `requirements-ml.txt`."""


def build_embedder(model_name: str, device: str | None = None, max_tokens: int = 1024) -> Embedder:
    """Même fabrique à l'indexation et à la requête : les deux utilisent forcément le même modèle."""
    if model_name == HASHING_MODEL:
        from backend.rag.fake import HashingEmbedder

        return HashingEmbedder(model_name=model_name)
    return BgeM3Embedder(model_name, device=device, max_tokens=max_tokens)


class BgeM3Embedder:
    """`max_tokens` tronque les textes trop longs : BGE-M3 accepte 8 192 tokens, mais l'attention
    sur des lots de textes aussi longs sature la mémoire d'un serveur sans GPU. Le plein texte
    reste indexé en entier par PostgreSQL."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str | None = None,
        batch_size: int = 16,
        max_tokens: int = 1024,
    ):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model = SentenceTransformer(model_name, device=device)
        self._model.max_seq_length = max_tokens
        self.dimension = self._model.get_sentence_embedding_dimension()
        self._batch_size = batch_size

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text])[0]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(list(texts))

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,
        )
        return vectors.tolist()


class NoopReranker:
    """V0 : garde l'ordre de la recherche hybride."""

    def rerank(self, question: str, passages: Sequence[Passage], top_n: int) -> list[Passage]:
        return list(passages[:top_n])


class CrossEncoderReranker:
    """bge-reranker-v2-m3. Remplace `relevance` par le score du reranker (sigmoïde, dans [0, 1]) :
    le seuil `JULIA_MIN_RELEVANCE` doit être recalibré quand on l'active.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str | None = None):
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model_name, device=device, max_length=512)

    def rerank(self, question: str, passages: Sequence[Passage], top_n: int) -> list[Passage]:
        if not passages:
            return []
        scores = self._model.predict([(question, passage.content) for passage in passages])
        ranked = sorted(
            zip(passages, scores, strict=True),
            key=lambda item: (item[0].exact_match, float(item[1])),
            reverse=True,
        )
        return [dataclasses.replace(passage, relevance=float(score)) for passage, score in ranked[:top_n]]
