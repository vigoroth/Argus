from langchain_core.tools import tool

from app.rag.hybrid import hybrid_search_expanded


@tool
def search_documents(query: str) -> str:
    """Search the user's personal knowledge base of ingested documents.
    ALWAYS use this for questions about the user's notes, saved documents,
    or anything in "my documents". Searches an indexed database (hybrid
    semantic + keyword with reranking), NOT the filesystem.
    """
    chunks = hybrid_search_expanded(query, top_k=4)
    if not chunks:
        return "No relevant documents found."
    blocks = [f"[{i}] {c}" for i, c in enumerate(chunks, 1)]
    return "\n\n".join(blocks)