"""Cross-encoder reranking — re-score retrieval candidates by reading
the query and each chunk together. Runs locally, no API.
"""
from functools import lru_cache

from sentence_transformers import CrossEncoder


@lru_cache
def _get_reranker():
    # loaded once and cached; downloads the model on first use

    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(query: str, candidates: list[str], top_k: int = 4) -> list[str]:
    """Re-score candidates against the query, return the best top_k."""
    if not candidates:
        return []
    model = _get_reranker()
    # the model scores each (query, chunk) pair for relevance
    pairs = [(query, c) for c in candidates]
    scores = model.predict(pairs)
    # pair each candidate with its score, sort high to low
    ranked = sorted(zip(candidates, scores, strict=False), key=lambda x: x[1], reverse=True)
    return [text for text, _ in ranked[:top_k]]