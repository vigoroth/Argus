"""Toolgate: gated draft → approve → hot-load of agent-written tools (Upgrade 006)."""
import pytest

from app.skills import toolgate

GOOD_TOOL = '''
from langchain_core.tools import tool

@tool
def shout(text: str) -> str:
    """Uppercase the text."""
    return text.upper()

TOOLS = [shout]
'''


@pytest.fixture()
def tool_dirs(tmp_path, monkeypatch):
    custom = tmp_path / "custom"
    custom.mkdir()
    monkeypatch.setattr(toolgate, "CUSTOM_DIR", custom)
    monkeypatch.setattr(toolgate, "PENDING_TOOLS_DIR", custom / "_pending")
    return custom


def test_draft_approve_load(tool_dirs):
    toolgate.draft_tool("shout-tool", GOOD_TOOL)
    assert [t["name"] for t in toolgate.list_pending_tools()] == ["shout-tool"]
    assert toolgate.load_custom_tools() == []            # pending is inert
    assert toolgate.approve_tool("shout-tool") is True
    assert toolgate.list_pending_tools() == []
    tools = toolgate.load_custom_tools()
    assert [t.name for t in tools] == ["shout"]
    assert tools[0].invoke({"text": "hi"}) == "HI"       # actually executable now


def test_reject_deletes(tool_dirs):
    toolgate.draft_tool("bad-tool", GOOD_TOOL)
    assert toolgate.reject_tool("bad-tool") is True
    assert toolgate.list_pending_tools() == []
    assert toolgate.reject_tool("bad-tool") is False


def test_guards(tool_dirs):
    with pytest.raises(ValueError):
        toolgate.draft_tool("../evil", GOOD_TOOL)
    with pytest.raises(ValueError):
        toolgate.draft_tool("no-tools-list", "print('hi')")   # must define TOOLS
    assert toolgate.approve_tool("../evil") is False
    assert toolgate.reject_tool("../evil") is False


def test_broken_module_skipped(tool_dirs):
    (tool_dirs / "broken.py").write_text("raise RuntimeError('boom')\nTOOLS = []\n")
    toolgate.draft_tool("fine", GOOD_TOOL)
    toolgate.approve_tool("fine")
    tools = toolgate.load_custom_tools()                 # broken skipped, fine loads
    assert [t.name for t in tools] == ["shout"]
