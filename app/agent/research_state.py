"""State schema for the deep-research orchestrator (Upgrade 001).

Kept separate from AgentState so the main ReAct graph is untouched. The `findings`
field is the map-reduce accumulator: parallel `researcher` branches each append one
entry, so it MUST carry a reducer (`operator.add`) or concurrent writes clobber each
other — see lab/reference/agents-and-subagents.md.
"""
import operator
from typing import Annotated, TypedDict


class ResearchState(TypedDict, total=False):
    question: str                              # the user's research question
    plan: list[str]                            # sub-questions (post-approval)
    findings: Annotated[list[dict], operator.add]  # [{subq, summary, sources[]}] — reducer!
    report: str                                # final synthesized markdown


class ResearcherInput(TypedDict):
    """Per-subagent input carried by each Send()."""
    subq: str
