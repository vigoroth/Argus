"""Hook system (Upgrade 009): registry semantics, built-in gates, hooked tool node."""
import pytest
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import tool

import app.hooks.builtin  # noqa: F401 — registers the built-ins
from app.hooks import registry
from app.hooks.builtin import block_destructive_shell, inject_datetime
from app.hooks.registry import (
    hook,
    run_post_tool_use,
    run_pre_tool_use,
    run_session_start,
)
from app.hooks.toolnode import make_hooked_tool_node

# ── registry semantics (isolated event namespace via clear + re-register) ──

def test_unknown_event_rejected():
    with pytest.raises(ValueError):
        hook("on_full_moon")


def test_pre_block_first_wins_and_fail_closed(monkeypatch):
    calls = []
    monkeypatch.setattr(registry, "_HOOKS", {e: [] for e in registry.EVENTS})

    @hook("pre_tool_use")
    def crashing(name, args):
        calls.append("crash")
        raise RuntimeError("boom")

    @hook("pre_tool_use")
    def never_reached(name, args):
        calls.append("late")
        return None

    reason = run_pre_tool_use("anything", {})
    assert "blocked" in reason          # crash -> fail closed
    assert calls == ["crash"]           # short-circuit: later gate not consulted


def test_session_start_hook_errors_swallowed(monkeypatch):
    monkeypatch.setattr(registry, "_HOOKS", {e: [] for e in registry.EVENTS})

    @hook("session_start")
    def broken(state):
        raise RuntimeError("nope")

    @hook("session_start")
    def fine(state):
        return [SystemMessage(content="ok")]

    msgs = run_session_start({})
    assert [m.content for m in msgs] == ["ok"]


def test_post_never_raises(monkeypatch):
    monkeypatch.setattr(registry, "_HOOKS", {e: [] for e in registry.EVENTS})

    @hook("post_tool_use")
    def broken(name, args, result, ms):
        raise RuntimeError("nope")

    run_post_tool_use("t", {}, "r", 1.0)  # must not raise


# ── built-ins ────────────────────────────────────────────────────────────────

def test_builtin_datetime_injects():
    msgs = inject_datetime({})
    assert len(msgs) == 1 and "Current date/time:" in msgs[0].content


def test_builtin_destructive_gate():
    assert block_destructive_shell("run_shell", {"command": "rm -rf /"}) is not None
    assert block_destructive_shell("run_shell", {"command": "ls -la"}) is None
    assert block_destructive_shell("read_file", {"path": "rm -rf /"}) is None


# ── hooked tool node ─────────────────────────────────────────────────────────

@tool
def echo(text: str) -> str:
    """Echo the text back."""
    return f"echo:{text}"


def _ai_with_calls(*calls):
    return AIMessage(content="", tool_calls=[
        {"name": n, "args": a, "id": f"c{i}", "type": "tool_call"}
        for i, (n, a) in enumerate(calls)])


@pytest.mark.asyncio
async def test_tool_node_executes_and_blocks(monkeypatch):
    monkeypatch.setattr(registry, "_HOOKS", {e: [] for e in registry.EVENTS})
    registry._HOOKS["pre_tool_use"].append(block_destructive_shell)
    seen = []
    registry._HOOKS["post_tool_use"].append(
        lambda name, args, result, ms: seen.append(name))

    node = make_hooked_tool_node([echo])
    out = await node({"messages": [_ai_with_calls(
        ("echo", {"text": "hi"}),
        ("run_shell", {"command": "rm -rf /"}),   # blocked by gate (tool not even bound)
        ("missing_tool", {}),
    )]})
    msgs = out["messages"]
    assert msgs[0].content == "echo:hi"
    assert "REFUSED by policy hook" in msgs[1].content
    assert "unknown tool" in msgs[2].content
    assert seen == ["echo", "run_shell", "missing_tool"]  # post saw everything
    assert all(m.tool_call_id == f"c{i}" for i, m in enumerate(msgs))
