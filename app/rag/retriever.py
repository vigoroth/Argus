from app.rag.store import get_pgvector_collection


def search(query: str, k: int = 4) -> list[dict]:
    """Find the k most relevant chunks for a query.

    Embeds the query, does a similarity search in pgvector, and returns
    the matching chunks with their text, source, and similarity score.
    """
    store = get_pgvector_collection()

    # similarity_search_with_score returns (Document, distance) tuples.
    # Lower distance = more similar (cosine distance).
    results = store.similarity_search_with_score(query, k=k)

    out = []
    for doc, score in results:
        out.append({
            "text": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "score": round(float(score), 4),
        })
    return out