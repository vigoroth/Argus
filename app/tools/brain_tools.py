from langchain_core.tools import tool

from app.brain.service import query_brain


@tool
def brain_query(question: str) -> str:
    """Search the canonical Second Brain vault for durable user knowledge,
    shipped evidence, active projects, or raw captures. Results are ordered by
    authority (wiki > output > projects > inbox) and cite Obsidian wikilinks.
    """
    results = query_brain(question)
    if not results:
        return "No related canonical brain notes found."
    return "\n\n".join(
        f"{r['wikilink']} ({r['stage']}, sha256={r['sha256']})\n{r['excerpt']}"
        for r in results
    )
