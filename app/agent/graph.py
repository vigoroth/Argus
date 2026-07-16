from dotenv import load_dotenv
from langchain_core.messages import RemoveMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

import app.hooks.builtin  # noqa: F401 — importing registers the built-in hooks
from app.agent.state import AgentState
from app.agent.summarize import choose_cut, count_tokens, prunable, render_messages
from app.core.llm import get_llm, invoke_tracked
from app.core.logging_config import get_logger
from app.hooks.registry import run_session_start
from app.hooks.toolnode import make_hooked_tool_node
from app.mcp.client import load_mcp_tools
from app.tools.agent_tools import AGENT_TOOLS
from app.tools.brain_tools import brain_query
from app.tools.calendar_tools import CALENDAR_TOOLS
from app.tools.idea_tools import IDEA_TOOLS
from app.tools.metrics_tools import METRICS_TOOLS
from app.tools.os_tools import list_dir, read_file, run_shell
from app.tools.rag_tool import search_documents
from app.tools.skill_tools import SKILL_TOOLS
from app.tools.web_search import web_search

load_dotenv()

log = get_logger("argus.agent.graph")


SYSTEM_PROMPT = """You are a helpful personal AI assistant named Argus with access to tools.

Tool selection rules:
- For anything about the user's OWN notes, documents, saved advice, or "my
  documents/files", use search_documents. This is a vector search over their
  ingested knowledge base, not the filesystem.
- Use read_file / list_dir / run_shell only for actual filesystem paths the
  user explicitly names.
- To recall durable user knowledge, shipped evidence, active projects, or raw
  captures, use brain_query. Canonical authority is wiki > output > projects >
  inbox. Cite returned [[wikilinks]] and preserve contradictions.
- Use web_search to find pages by topic. To read the full contents of a specific
  URL or web page you already have, use the fetch tool (retrieves and extracts
  page content as markdown). For current events, recent news, prices, or facts
  that may have changed, use web_search; for the user's own documents use
  search_documents.
- To schedule, view, find, or cancel the user's events, use the calendar tools
  (add_event / list_events / find_events / delete_event). Pass datetimes as ISO
  8601 (e.g. 2026-07-10T15:00); resolve relative dates like "friday" against the
  current date/time given below. Before delete_event, confirm which event with the
  user (look up its id first).
- SKILLS: your context lists available skills (one line each). Before improvising a
  multi-step workflow, check that list — if a skill matches the task, call
  load_skill(name) and follow its instructions. If the task needs a reusable
  workflow no skill covers, draft one with create_skill (it goes to a human
  approval queue; tell the user to approve it in the Skills tab).
- SUBAGENTS: for substantial delegable work (data analysis, long research legs),
  check the subagents list and use spawn_agent(name, task) with ONE self-contained
  task. If a task needs an executable capability no tool provides, draft it with
  create_tool (Python module defining TOOLS = [...]); it requires human code review
  in the Skills tab before it can run.

Think step by step. Be concise. When you answer from search_documents results,
cite the source numbers like [1], [2].

Durable memory capture is enforced deterministically by the runtime. Do not
claim a fact was saved unless an activity event confirms the brain transaction."""


# Long-thread summarization: once a thread exceeds the token budget (or message
# count as a floor), fold everything older than the KEEP_RECENT most-recent messages
# into a running summary and prune it from the persisted checkpoint, so the model's
# working context stays bounded.
SUMMARY_TRIGGER_TOKENS = 3000
SUMMARY_TRIGGER_MSGS = 20
SUMMARY_KEEP_RECENT = 8

SUMMARY_SYSTEM = (
    "You maintain a running summary of an ongoing conversation between a user and an "
    "AI assistant. Given the existing summary and the next slice of messages, return a "
    "single updated summary that preserves durable facts, decisions, open threads, and "
    "user preferences. Be concise; drop pleasantries and redundant back-and-forth."
)


def summarize_node(state: AgentState) -> dict:
    """Runs once per user turn (START → summarize → llm). No-op until the thread
    grows past the trigger; then summarizes the older prefix and prunes it."""
    msgs = state["messages"]
    # trigger on token budget, with message count as a secondary floor
    if count_tokens(msgs) <= SUMMARY_TRIGGER_TOKENS and len(msgs) <= SUMMARY_TRIGGER_MSGS:
        return {}
    to_prune = prunable(msgs, choose_cut(msgs, SUMMARY_KEEP_RECENT))
    if not to_prune:
        return {}
    prior = state.get("summary") or ""
    prompt = (
        f"Existing summary:\n{prior or '(none)'}\n\n"
        f"New messages to fold in:\n{render_messages(to_prune)}\n\n"
        "Return the updated summary."
    )
    try:
        result = invoke_tracked(prompt, system=SUMMARY_SYSTEM)
    except Exception as e:  # summarization must never break the chat turn
        log.warning("summarization skipped: %s", e)
        return {}
    removals = [RemoveMessage(id=m.id) for m in to_prune]
    return {"summary": result.text, "messages": removals}


async def build_graph(checkpointer=None, model: str | None = None,
                      provider: str | None = None,
                      memory_backend: str = "both",
                      plain: bool = False):
        """Build the agent graph with canonical Second Brain retrieval.

        ``memory_backend`` remains for evaluation-call compatibility; durable
        runtime recall comes from ``brain_query`` and request-scoped Brain context.
        plain=True → no tools bound at all (UI 'Chat' mode: direct LLM answer,
        still with conversation memory + relevant Brain context injected)."""
        if plain:
            all_tools = []
        else:
            mcp_tools = await load_mcp_tools()

            # all MCP tools (fetch, filesystem, ...) flow through as-is
            other_mcp = mcp_tools

            # base tools (always present)
            # approved agent-written tools (app/tools/custom/) hot-load here;
            # the server clears the graph cache on approval so this re-runs
            from app.skills.toolgate import load_custom_tools
            custom = load_custom_tools()

            base = [search_documents, web_search, read_file, list_dir, run_shell,
                    brain_query] + CALENDAR_TOOLS + SKILL_TOOLS + IDEA_TOOLS \
                + METRICS_TOOLS + AGENT_TOOLS + custom + other_mcp

            # Postgres long-term memory tools (kept toggleable for backend experiments)
            all_tools = base
        llm = get_llm(streaming=True, model=model, provider=provider)
        if all_tools:
            llm = llm.bind_tools(all_tools)
        
        async def llm_node(state: AgentState) -> dict:
                    from langchain_core.messages import HumanMessage

                    messages = [SystemMessage(content=SYSTEM_PROMPT)]

                    # session_start hooks: deterministic per-turn context injection
                    # (datetime, skills index, subagent index, calendar reminders).
                    # Runtime-pushed, never model-controlled — see app/hooks/builtin.py.
                    messages += run_session_start(state)

                    # running summary of older, pruned turns (trusted — we generated it)
                    summary = state.get("summary")
                    if summary:
                        messages.append(SystemMessage(
                            content="[SUMMARY OF EARLIER CONVERSATION]\n" + summary))

                    brain_context = state.get("brain_context")
                    if brain_context:
                        messages.append(HumanMessage(content=brain_context))

                    messages += state["messages"]
                    response = llm.invoke(messages)
                    return {"messages": [response]}

        def should_continue(state: AgentState) -> str:
            """Decide: loop back to tools, or stop and return the answer."""
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            return "end"

        async def summarize_async(state: AgentState) -> dict:
            # LangGraph runs synchronous nodes in asyncio's default executor.
            # Python 3.13 can then hang while closing that executor, even when
            # the node is a no-op. Keep the pure sync function for unit tests,
            # but register an async wrapper in the runtime graph.
            return summarize_node(state)

        graph = StateGraph(AgentState)
        graph.add_node("summarize", summarize_async)
        graph.add_node("llm", llm_node)
        graph.add_edge(START, "summarize")
        graph.add_edge("summarize", "llm")

        if all_tools:
            # hook-aware tool executor: pre_tool_use can veto a call (the model
            # sees the block reason as the tool result), post_tool_use logs all
            graph.add_node("tools", make_hooked_tool_node(all_tools))
            graph.add_conditional_edges(
                "llm",
                should_continue,
                {"tools": "tools", "end": END},
            )
            graph.add_edge("tools", "llm")
        else:  # plain chat: one LLM turn, no tool loop
            graph.add_edge("llm", END)

        return graph.compile(checkpointer=checkpointer)
