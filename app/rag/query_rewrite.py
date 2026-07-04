"""Query rewriting and multi-query expansion using the LLM.
Turns a raw user question into focused search queries before retrieval.
"""
from app.core.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage


REWRITE_SYSTEM = """You rewrite a user's question into search queries for a \
document retrieval system. Output ONLY the queries, one per line, no numbering, \
no explanation. Generate 3 short, focused queries that capture different \
phrasings or aspects of the question."""


def expand_query(question: str) -> list[str]:
    """Generate multiple focused search queries from one question."""
    llm = get_llm()
    resp = llm.invoke([
        SystemMessage(content=REWRITE_SYSTEM),
        HumanMessage(content=question),
    ])
    # split the reply into individual query lines
    lines = [ln.strip() for ln in resp.content.splitlines() if ln.strip()]
    # always include the original question as a fallback
    queries = lines[:3] if lines else []
    queries.append(question)
    return queries