"""Web search tool — free DuckDuckGo search, no API key.

Gives the agent access to current information beyond its training data.
"""
from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """Search the web for current information.
    Use this for recent events, current facts, news, prices, or anything
    that may have changed or happened after your training data.
    Do NOT use this for the user's own saved documents (use search_documents)
    or for their personal facts (use load_memory).
    """
    try:
        from ddgs import DDGS
    except ImportError:
        return "ERROR: web search unavailable (ddgs not installed)."

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except Exception as e:
        return f"ERROR: web search failed: {e}"

    if not results:
        return "No results found."

    blocks = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("href", "")
        body = r.get("body", "")[:300]
        blocks.append(f"[{i}] {title}\n{url}\n{body}")
    return "\n\n".join(blocks)