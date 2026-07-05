"""Pure summarization helpers in app/agent/summarize.py (no LLM/DB needed)."""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent.summarize import choose_cut, count_tokens, prunable, render_messages


def test_render_messages_roles_and_tool_calls():
    msgs = [
        HumanMessage(content="hi there", id="1"),
        AIMessage(content="", tool_calls=[{"name": "web_search", "args": {}, "id": "x"}], id="2"),
        ToolMessage(content="a result", tool_call_id="x", name="web_search", id="3"),
    ]
    out = render_messages(msgs)
    assert "user: hi there" in out
    assert "[called: web_search]" in out
    assert "tool: a result" in out


def test_render_skips_empty_content():
    msgs = [HumanMessage(content="", id="1"), HumanMessage(content="kept", id="2")]
    assert render_messages(msgs) == "user: kept"


def test_choose_cut_keeps_recent():
    msgs = [HumanMessage(content=str(i), id=str(i)) for i in range(10)]
    # keep last 3 verbatim → cut at index 7
    assert choose_cut(msgs, 3) == 7


def test_choose_cut_never_starts_on_tool_message():
    # if the natural cut lands on a ToolMessage, push forward so its parent
    # AIMessage tool_calls are not orphaned in the kept window
    msgs = [HumanMessage(content=str(i), id=str(i)) for i in range(6)]
    msgs.append(AIMessage(content="", tool_calls=[{"name": "t", "args": {}, "id": "x"}], id="6"))
    msgs.append(ToolMessage(content="r", tool_call_id="x", name="t", id="7"))  # index 7
    msgs.append(HumanMessage(content="next", id="8"))
    # keep_recent=2 → natural cut at index 7 (a ToolMessage) → pushed to 8
    assert choose_cut(msgs, 2) == 8


def test_count_tokens_grows_with_content():
    short = [HumanMessage(content="hi", id="1")]
    long = [HumanMessage(content="word " * 500, id="1")]
    assert count_tokens(short) >= 0
    assert count_tokens(long) > count_tokens(short)


def test_choose_cut_clamps_to_zero():
    msgs = [HumanMessage(content="a", id="1")]
    assert choose_cut(msgs, 5) == 0


def test_prunable_excludes_idless_messages():
    with_id = HumanMessage(content="a", id="1")
    without_id = SystemMessage(content="b")  # no id assigned
    without_id.id = None
    pruned = prunable([with_id, without_id], cut=2)
    assert pruned == [with_id]
