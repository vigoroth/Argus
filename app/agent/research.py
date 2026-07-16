"""Deep-research orchestrator (Upgrade 001) — "plan mode" for Argus.

Pipeline:  question → plan → [human approves/edits] → parallel researchers → synthesize.

- plan_node       decomposes the question into independent sub-questions.
- approve_gate     interrupts for human approval/edit (LangGraph human-in-the-loop).
- dispatch         fans out one Send() per approved sub-question (map).
- researcher_node  a ReAct sub-agent (create_react_agent) researches ONE sub-question
                   in isolated context; appends a finding (reduce via operator.add).
- synthesize_node  integrates all findings into one cited markdown report (streamed).

See lab/reference/deep-agents.md for the theory.
"""
import json
import re

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Send, interrupt

from app.agent.research_state import ResearchState
from app.core.llm import get_llm
from app.core.logging_config import get_logger
from app.mcp.client import load_mcp_tools
from app.tools.brain_tools import brain_query
from app.tools.rag_tool import search_documents
from app.tools.tavily_search import tavily_search
from app.tools.web_search import web_search

log = get_logger("argus.agent.research")

MAX_SUBQUESTIONS = 5

PLANNER_SYSTEM = (
    "You are the planner of a deep-research system. Given a research question, break it "
    "into 2-5 INDEPENDENT sub-questions that can each be researched on their own and "
    "together fully answer the question. Prefer fewer, high-signal sub-questions. "
    "Return ONLY a JSON array of strings, nothing else. Example: "
    '["What is X?", "How does X compare to Y?", "What are the risks of X?"]'
)

RESEARCHER_SYSTEM = (
    "You are a focused research sub-agent. Research the ONE sub-question you are given "
    "using your tools. Prefer tavily_search; fall back to web_search + fetch to read "
    "specific pages. Use search_documents for ingested source documents and brain_query "
    "for canonical personal knowledge. Gather 2-4 solid sources, then write a concise "
    "factual summary "
    "(<200 words) that answers the sub-question. ALWAYS list the source URLs you used at "
    "the end under a 'Sources:' line. Do not speculate beyond your sources."
)

SYNTH_SYSTEM = (
    "You are the synthesizer of a deep-research system. Given the original question and "
    "the findings from several sub-researchers (each with its own sources), write a "
    "clear, well-structured markdown report that directly answers the question. Integrate "
    "the findings (don't just concatenate them), use ## section headings, and include a "
    "final '## Sources' section listing the unique URLs cited. Be objective and note "
    "disagreements or gaps between sources."
)


def _parse_plan(text: str) -> list[str]:
    """Extract the sub-question list from the planner's output (JSON, else lines)."""
    text = text.strip()
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            items = json.loads(m.group(0))
            subqs = [str(s).strip() for s in items if str(s).strip()]
            if subqs:
                return subqs[:MAX_SUBQUESTIONS]
        except json.JSONDecodeError:
            pass
    # fallback: non-empty lines, stripped of list markers
    lines = [re.sub(r"^\s*[-*\d.)]+\s*", "", ln).strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln][:MAX_SUBQUESTIONS]


async def build_research_graph(checkpointer=None, model: str | None = None,
                               provider: str | None = None):
    """Compile the research orchestrator. Async because sub-researchers need the MCP
    fetch tool (loaded async). Reuses get_llm + the standard research tools."""
    mcp_tools = await load_mcp_tools()
    fetch_tools = [t for t in mcp_tools if t.name == "fetch"]
    researcher_tools = [tavily_search, web_search, search_documents,
                        brain_query] + fetch_tools

    # sub-researcher: a self-contained ReAct agent with an isolated context
    researcher_llm = get_llm(streaming=True, model=model, provider=provider)
    researcher_agent = create_react_agent(
        researcher_llm, researcher_tools, prompt=RESEARCHER_SYSTEM)

    def plan_node(state: ResearchState) -> dict:
        llm = get_llm(model=model, provider=provider)
        resp = llm.invoke([
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": state["question"]},
        ])
        plan = _parse_plan(resp.content if isinstance(resp.content, str) else str(resp.content))
        if not plan:  # never leave the plan empty
            plan = [state["question"]]
        return {"plan": plan}

    def approve_gate(state: ResearchState) -> dict:
        """Pause for the human. The value passed to Command(resume=...) comes back here:
        an edited list replaces the plan; anything else keeps the proposed plan."""
        approved = interrupt({"plan": state["plan"]})
        if isinstance(approved, list) and approved:
            return {"plan": [str(s).strip() for s in approved if str(s).strip()]}
        return {}

    def dispatch(state: ResearchState):
        """Conditional edge: fan out one researcher per sub-question (map)."""
        return [Send("researcher", {"subq": q}) for q in state["plan"]]

    async def researcher_node(payload: dict) -> dict:
        subq = payload["subq"]
        try:
            result = await researcher_agent.ainvoke(
                {"messages": [HumanMessage(content=subq)]})
            summary = result["messages"][-1].content
        except Exception as e:  # one researcher failing must not sink the run
            log.warning("researcher failed for %r: %s", subq, e)
            summary = f"(research failed: {e})"
        sources = re.findall(r"https?://\S+", summary)
        return {"findings": [{"subq": subq, "summary": summary, "sources": sources}]}

    def synthesize_node(state: ResearchState) -> dict:
        findings = state.get("findings", [])
        blocks = []
        for f in findings:
            blocks.append(f"### Sub-question: {f['subq']}\n{f['summary']}")
        prompt = (
            f"Original question: {state['question']}\n\n"
            f"Findings from {len(findings)} sub-researchers:\n\n"
            + "\n\n".join(blocks)
            + "\n\nWrite the final report."
        )
        llm = get_llm(streaming=True, model=model, provider=provider)
        resp = llm.invoke([
            {"role": "system", "content": SYNTH_SYSTEM},
            {"role": "user", "content": prompt},
        ])
        return {"report": resp.content}

    g = StateGraph(ResearchState)
    g.add_node("plan", plan_node)
    g.add_node("approve", approve_gate)
    g.add_node("researcher", researcher_node)
    g.add_node("synthesize", synthesize_node)

    g.add_edge(START, "plan")
    g.add_edge("plan", "approve")
    g.add_conditional_edges("approve", dispatch, ["researcher"])
    g.add_edge("researcher", "synthesize")
    g.add_edge("synthesize", END)

    return g.compile(checkpointer=checkpointer)
