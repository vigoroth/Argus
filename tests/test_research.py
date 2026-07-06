"""Deep-research orchestrator: plan parsing + the parallel-safe findings reducer."""
import operator
import typing

from app.agent.research import MAX_SUBQUESTIONS, _parse_plan
from app.agent.research_state import ResearchState


def test_parse_plan_json():
    assert _parse_plan('["What is X?", "Risks of X?"]') == ["What is X?", "Risks of X?"]


def test_parse_plan_json_embedded_in_prose():
    text = 'Here is the plan:\n["a", "b"]\nHope that helps.'
    assert _parse_plan(text) == ["a", "b"]


def test_parse_plan_lines_fallback():
    assert _parse_plan("1. First q\n2. Second q\n- third") == ["First q", "Second q", "third"]


def test_parse_plan_caps():
    many = "[" + ",".join(f'"q{i}"' for i in range(20)) + "]"
    assert len(_parse_plan(many)) == MAX_SUBQUESTIONS


def test_parse_plan_empty():
    assert _parse_plan("") == []


def test_findings_uses_add_reducer():
    """Parallel researchers append concurrently — the reducer MUST be operator.add,
    or fan-out writes clobber each other (the classic map-reduce bug)."""
    hints = typing.get_type_hints(ResearchState, include_extras=True)
    findings = hints["findings"]
    assert typing.get_args(findings)[1] is operator.add
