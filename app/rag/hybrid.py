"""Hybrid retrieval: dense (pgvector) + sparse (Postgres full-text),
fused with Reciprocal Rank Fusion (RRF).
"""
import psycopg

from app.core.config import get_settings
from app.rag.query_rewrite import expand_query
from app.rag.rerank import rerank
from app.rag.store import get_pgvector_collection


def _conn():
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(url)


def _dense_search(query: str, k: int = 20) -> list[str]:
    """Return chunk texts ranked by vector similarity."""
    store = get_pgvector_collection()
    results = store.similarity_search(query, k=k)
    return [doc.page_content for doc in results]


def _sparse_search(query: str, k: int = 20) -> list[str]:
    """Return chunk texts ranked by Postgres full-text relevance."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT document FROM langchain_pg_embedding "
            "WHERE fts @@ plainto_tsquery('english', %s) "
            "ORDER BY ts_rank(fts, plainto_tsquery('english', %s)) DESC "
            "LIMIT %s",
            (query, query, k),
        ).fetchall()
    return [r[0] for r in rows]


def _rrf_fuse(dense: list[str], sparse: list[str], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion of two ranked lists of chunk texts."""
    scores: dict[str, float] = {}
    for rank, text in enumerate(dense):
        scores[text] = scores.get(text, 0.0) + 1.0 / (k + rank)
    for rank, text in enumerate(sparse):
        scores[text] = scores.get(text, 0.0) + 1.0 / (k + rank)
    # sort by fused score, highest first
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [text for text, _ in ranked]


def hybrid_search_expanded(question: str, top_k: int = 4, per_query: int = 15) -> list[str]:
    """Expand the question into multiple queries, search each, pool, rerank."""


    queries = expand_query(question)

    # pool candidates from all query variations (dedup by text)
    pool: dict[str, None] = {}
    for q in queries:
        dense = _dense_search(q, k=per_query)
        sparse = _sparse_search(q, k=per_query)
        for text in _rrf_fuse(dense, sparse):
            pool[text] = None  # dict preserves insertion order, dedupes

    # rerank the whole pool against the ORIGINAL question
    return rerank(question, list(pool.keys()), top_k=top_k)