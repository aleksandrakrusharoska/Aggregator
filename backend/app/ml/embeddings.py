"""Embeddings — sentence-transformers (мултијазичен модел, работи и за македонски)."""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = _model().encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]
