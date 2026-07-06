"""Subagent registry: AGENT.md parsing + tool allowlist resolution (Upgrade 006)."""
from app.subagents import loader, registry


def _mk_agent(root, name, tools="read_file, list_dir"):
    d = root / name
    d.mkdir(parents=True)
    (d / "AGENT.md").write_text(
        f"---\nname: {name}\ndescription: does {name} things\ntools: {tools}\n---\n\n"
        f"You are the {name} agent.\n")


def test_parse_agent(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "AGENTS_DIR", tmp_path)
    _mk_agent(tmp_path, "helper")
    a = loader.get_agent("helper")
    assert a["name"] == "helper"
    assert a["tools"] == ["read_file", "list_dir"]
    assert "You are the helper agent." in a["body"]


def test_index_and_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "AGENTS_DIR", tmp_path)
    _mk_agent(tmp_path, "alpha")
    _mk_agent(tmp_path, "beta")
    idx = loader.agent_index()
    assert "- alpha: does alpha things" in idx and "beta" in idx
    assert loader.get_agent("nope") is None
    assert loader.get_agent("../etc") is None  # slug guard via skills loader


def test_resolve_tools_skips_unknown():
    tools = registry.resolve_tools(["read_file", "made_up_tool", "run_shell"])
    assert [t.name for t in tools] == ["read_file", "run_shell"]


def test_builtin_data_analyst_loads():
    a = loader.get_agent("data-analyst")  # the real committed definition
    assert a is not None
    resolved = registry.resolve_tools(a["tools"])
    assert {t.name for t in resolved} == {"read_file", "list_dir", "run_shell",
                                          "query_metrics"}
