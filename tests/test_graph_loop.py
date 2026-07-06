"""ReAct loop coverage (Upgrade 012): message assembly, tool routing, summarization.

The LLM is faked (scripted responses); everything else — graph wiring, hooks,
the hooked tool node, summarize_node — is real.
"""
import asyncio

import pytest
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

import app.agent.graph as graph_mod
from app.agent.graph import SYSTEM_PROMPT, build_graph, summarize_node


class FakeLLM:
    """Returns scripted AIMessages; records every prompt it was invoked with."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[list] = []

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.calls.append(list(messages))
        return self.responses.pop(0)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def no_mcp(monkeypatch):
    async def none():
        return []
    monkeypatch.setattr(graph_mod, "load_mcp_tools", none)


def test_plain_graph_message_assembly(monkeypatch):
    fake = FakeLLM([AIMessage(content="hi there")])
    monkeypatch.setattr(graph_mod, "get_llm", lambda **kw: fake)
    monkeypatch.setattr("app.memory.long_term.recall_all", lambda: {"pet_cat": "Mochi"})

    g = _run(build_graph(plain=True))
    out = _run(g.ainvoke({"messages": [HumanMessage(content="hello")]}))

    assert out["messages"][-1].content == "hi there"
    sent = fake.calls[0]
    assert sent[0].content == SYSTEM_PROMPT                       # system first
    joined = "\n".join(str(m.content) for m in sent)
    assert "Current date/time:" in joined                         # session_start hook ran
    # stored memory injected as explicitly untrusted data, never instructions
    mem = [m for m in sent if "STORED MEMORY" in str(m.content)]
    assert mem and "Mochi" in mem[0].content and mem[0].type == "human"


def test_tool_roundtrip_and_routing(monkeypatch, no_mcp, tmp_path):
    """llm asks for a tool -> tools node runs it -> llm sees result -> END."""
    (tmp_path / "hello.txt").write_text("x")
    fake = FakeLLM([
        AIMessage(content="", tool_calls=[{"name": "list_dir",
                                           "args": {"path": str(tmp_path)},
                                           "id": "tc1", "type": "tool_call"}]),
        AIMessage(content="done"),
    ])
    monkeypatch.setattr(graph_mod, "get_llm", lambda **kw: fake)
    monkeypatch.setattr("app.memory.long_term.recall_all", lambda: {})

    g = _run(build_graph())
    out = _run(g.ainvoke({"messages": [HumanMessage(content="what files?")]}))

    assert out["messages"][-1].content == "done"                  # routed back then END
    tool_msgs = [m for m in out["messages"] if m.type == "tool"]
    assert len(tool_msgs) == 1 and "hello.txt" in tool_msgs[0].content
    assert len(fake.calls) == 2                                   # llm -> tools -> llm


def test_policy_gate_inside_the_loop(monkeypatch, no_mcp):
    """A destructive run_shell call is vetoed by the pre-hook, turn survives."""
    fake = FakeLLM([
        AIMessage(content="", tool_calls=[{"name": "run_shell",
                                           "args": {"command": "rm -rf /"},
                                           "id": "tc1", "type": "tool_call"}]),
        AIMessage(content="understood"),
    ])
    monkeypatch.setattr(graph_mod, "get_llm", lambda **kw: fake)
    monkeypatch.setattr("app.memory.long_term.recall_all", lambda: {})

    g = _run(build_graph())
    out = _run(g.ainvoke({"messages": [HumanMessage(content="wipe it")]}))

    tool_msgs = [m for m in out["messages"] if m.type == "tool"]
    assert "REFUSED by policy hook" in tool_msgs[0].content
    assert out["messages"][-1].content == "understood"


def test_summarize_noop_below_trigger():
    msgs = [HumanMessage(content="hi", id="m1")]
    assert summarize_node({"messages": msgs}) == {}


def test_summarize_prunes_above_trigger(monkeypatch):
    class R:
        text = "the summary"
    monkeypatch.setattr(graph_mod, "invoke_tracked", lambda *a, **kw: R())
    monkeypatch.setattr(graph_mod, "SUMMARY_TRIGGER_TOKENS", 1)
    monkeypatch.setattr(graph_mod, "SUMMARY_TRIGGER_MSGS", 4)

    msgs = []
    for i in range(12):  # alternating turns, all with ids (RemoveMessage needs them)
        cls = HumanMessage if i % 2 == 0 else AIMessage
        msgs.append(cls(content=f"turn {i} " + "x" * 50, id=f"m{i}"))
    out = summarize_node({"messages": msgs, "summary": None})

    assert out["summary"] == "the summary"
    removals = [m for m in out["messages"] if isinstance(m, RemoveMessage)]
    assert removals and len(removals) < len(msgs)                 # prunes prefix only


def test_summarize_failure_is_swallowed(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("llm down")
    monkeypatch.setattr(graph_mod, "invoke_tracked", boom)
    monkeypatch.setattr(graph_mod, "SUMMARY_TRIGGER_TOKENS", 1)
    monkeypatch.setattr(graph_mod, "SUMMARY_TRIGGER_MSGS", 2)
    msgs = [HumanMessage(content="x" * 80, id=f"m{i}") for i in range(8)]
    assert summarize_node({"messages": msgs}) == {}               # never breaks the turn
