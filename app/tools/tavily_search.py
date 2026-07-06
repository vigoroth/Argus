"""Research-grade web search via Tavily.

Complements the free `web_search` (DuckDuckGo): Tavily returns ranked, cleaned,
content-rich results tuned for LLM research. Requires TAVILY_API_KEY.

Fail-soft by design: with no key set, the tool returns a short notice instead of
raising, so a research sub-agent simply falls back to `web_search` + `fetch`. That
keeps deep research fully functional offline / key-less, just lower quality.
"""
import os

from langchain_core.tools import tool

from app.core.logging_config import get_logger

log = get_logger("argus.tools.tavily")


@tool
def tavily_search(query: str) -> str:
    """Search the web with Tavily for high-quality, research-oriented results.
    Prefer this over web_search when it is available; it returns ranked pages
    with extracted content. Use for current facts, news, and gathering sources.
    """
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return ("TAVILY_API_KEY not set — Tavily unavailable. "
                "Use web_search + fetch instead.")
    try:
        from tavily import TavilyClient
    except ImportError:
        return "ERROR: tavily-python not installed."

    try:
        client = TavilyClient(api_key=key)
        resp = client.search(query, max_results=5, search_depth="advanced")
    except Exception as e:
        log.warning("tavily search failed: %s", e)
        return f"ERROR: tavily search failed: {e}"

    results = resp.get("results", [])
    if not results:
        return "No results found."

    blocks = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = (r.get("content", "") or "")[:500]
        blocks.append(f"[{i}] {title}\n{url}\n{content}")
    return "\n\n".join(blocks)
