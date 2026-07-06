"""Tavily tool fail-soft behavior (no network in CI)."""
from app.tools.tavily_search import tavily_search


def test_no_key_fails_soft(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    out = tavily_search.invoke({"query": "anything"})
    assert "TAVILY_API_KEY not set" in out
    assert "web_search" in out  # points the agent at the fallback
