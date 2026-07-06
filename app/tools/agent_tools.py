"""Agent-factory tools (Upgrade 006): spawn a specialized subagent, or draft a
brand-new tool for human approval.

spawn_agent mirrors research.py's researcher_node: an isolated create_react_agent
run whose failure is caught, never fatal to the parent turn.
"""
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.core.llm import get_llm
from app.core.logging_config import get_logger
from app.skills import toolgate
from app.subagents.loader import get_agent, list_agents
from app.subagents.registry import resolve_tools

log = get_logger("argus.tools.agents")

MAX_SUBAGENT_STEPS = 25  # recursion cap: a runaway subagent stops, parent survives

# Subagents run on the SAME model/provider as the parent turn. The server sets
# this per chat request (single-user app; a concurrent different-model chat
# would race, which is acceptable here and documented).
_current_llm = {"model": None, "provider": None}


def set_subagent_llm(model: str | None, provider: str | None) -> None:
    _current_llm["model"] = model
    _current_llm["provider"] = provider


@tool
async def spawn_agent(name: str, task: str) -> str:
    """Delegate a task to a specialized subagent (see the agents list in your
    context). The subagent runs its own tool loop in isolated context and returns
    a final report. Give it ONE self-contained task with all needed details.
    """
    spec = get_agent(name)
    if spec is None:
        names = ", ".join(a["name"] for a in list_agents()) or "(none)"
        return f"ERROR: no agent named {name!r}. Available: {names}"
    tools = resolve_tools(spec["tools"])
    if not tools:
        return f"ERROR: agent {name!r} resolved zero tools — check its AGENT.md."
    llm = get_llm(streaming=False, model=_current_llm["model"],
                  provider=_current_llm["provider"])
    sub = create_react_agent(llm, tools, prompt=spec["body"])
    try:
        result = await sub.ainvoke(
            {"messages": [HumanMessage(content=task)]},
            config={"recursion_limit": MAX_SUBAGENT_STEPS},
        )
        return result["messages"][-1].content
    except Exception as e:  # a failing subagent must not sink the parent turn
        log.warning("subagent %r failed: %s", name, e)
        return f"ERROR: subagent {name!r} failed: {e}"


@tool
def create_tool(name: str, description: str, code: str) -> str:
    """Draft a NEW Python tool when a task needs a capability no existing tool
    covers. `name` is lowercase-kebab-case. `code` is a complete module: define
    functions decorated with @tool (from langchain_core.tools) and a module-level
    TOOLS = [...] list. The draft goes to a human approval queue (Skills tab) —
    it is NOT executable until approved.
    """
    try:
        toolgate.draft_tool(name, code)
    except ValueError as e:
        return f"ERROR: {e}"
    except Exception as e:  # pragma: no cover — fs errors
        return f"ERROR: {e}"
    return (f"Tool '{name}' drafted ({description}) — awaiting code review in the "
            "Skills tab. It becomes available after the user approves it.")


AGENT_TOOLS = [spawn_agent, create_tool]
