"""Tool allowlist resolution for spawned subagents (Upgrade 006).

An AGENT.md names its tools; this maps those names to the actual tool objects.
Static registry — a subagent can only ever receive tools that already exist and
are already trusted. Unknown names are skipped (logged), never guessed.
"""
from app.core.logging_config import get_logger
from app.tools.calendar_tools import CALENDAR_TOOLS
from app.tools.graph_query import graph_query
from app.tools.idea_tools import add_idea
from app.tools.metrics_tools import query_metrics
from app.tools.os_tools import list_dir, read_file, run_shell
from app.tools.rag_tool import search_documents
from app.tools.tavily_search import tavily_search
from app.tools.web_search import web_search

log = get_logger("argus.subagents.registry")

_REGISTRY = {
    "search_documents": search_documents,
    "web_search": web_search,
    "tavily_search": tavily_search,
    "read_file": read_file,
    "list_dir": list_dir,
    "run_shell": run_shell,
    "graph_query": graph_query,
    "query_metrics": query_metrics,
    "add_idea": add_idea,
    **{t.name: t for t in CALENDAR_TOOLS},
}


def resolve_tools(names: list[str], mcp_tools: list | None = None) -> list:
    """Allowlist names -> tool objects. MCP tools (fetch, …) resolve by name too."""
    by_name = dict(_REGISTRY)
    for t in mcp_tools or []:
        by_name.setdefault(t.name, t)
    out = []
    for n in names:
        tool_obj = by_name.get(n)
        if tool_obj is None:
            log.warning("subagent allowlist names unknown tool %r — skipped", n)
            continue
        out.append(tool_obj)
    return out
