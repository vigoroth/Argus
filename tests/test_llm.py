"""Provider dispatch in app/core/llm.py.

We stub the model classes and settings so no network or API key is needed —
this exercises the branch selection and the kwargs each provider is built with.
Doubles as coverage for the otherwise-unexercised Anthropic/Gemini branches.
"""
import sys
import types
from types import SimpleNamespace

import pytest

from app.core import llm


def _fake_settings(**overrides):
    base = dict(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.2,
        llm_max_tokens=1024,
        openai_api_key="sk-test",
        anthropic_api_key="ak-test",
        google_api_key="gk-test",
        llm_base_url=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class _Capture:
    """Records the kwargs it was constructed with."""
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture
def patch_settings(monkeypatch):
    def _apply(**overrides):
        monkeypatch.setattr(llm, "get_settings", lambda: _fake_settings(**overrides))
    return _apply


def test_openai_without_key_raises(patch_settings, monkeypatch):
    patch_settings(llm_provider="openai", openai_api_key="")
    monkeypatch.setattr(llm, "ChatOpenAI", _Capture)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        llm.get_llm()


def test_openai_path_builds_chatopenai(patch_settings, monkeypatch):
    patch_settings(llm_provider="openai")
    monkeypatch.setattr(llm, "ChatOpenAI", _Capture)
    model = llm.get_llm()
    assert model.kwargs["api_key"] == "sk-test"
    assert model.kwargs["model"] == "gpt-4o-mini"


def test_ollama_path_points_at_local_daemon(patch_settings, monkeypatch):
    patch_settings(llm_provider="ollama", llm_model="qwen3:8b")
    monkeypatch.setattr(llm, "ChatOpenAI", _Capture)
    model = llm.get_llm()
    assert model.kwargs["base_url"] == "http://localhost:11434/v1"
    assert model.kwargs["api_key"] == "ollama"
    assert model.kwargs["model"] == "qwen3:8b"


def test_default_model_falls_back_to_settings(patch_settings, monkeypatch):
    patch_settings(llm_provider="openai", llm_model="gpt-4o-mini")
    monkeypatch.setattr(llm, "ChatOpenAI", _Capture)
    model = llm.get_llm(model="default")
    assert model.kwargs["model"] == "gpt-4o-mini"


def test_anthropic_branch(patch_settings, monkeypatch):
    patch_settings(llm_provider="anthropic", llm_model="claude-opus-4-8")
    fake_mod = types.ModuleType("langchain_anthropic")
    fake_mod.ChatAnthropic = _Capture
    monkeypatch.setitem(sys.modules, "langchain_anthropic", fake_mod)
    model = llm.get_llm()
    assert model.kwargs["model"] == "claude-opus-4-8"
    assert model.kwargs["api_key"] == "ak-test"


def test_gemini_branch(patch_settings, monkeypatch):
    patch_settings(llm_provider="gemini", llm_model="gemini-2.0-flash")
    fake_mod = types.ModuleType("langchain_google_genai")
    fake_mod.ChatGoogleGenerativeAI = _Capture
    monkeypatch.setitem(sys.modules, "langchain_google_genai", fake_mod)
    model = llm.get_llm()
    assert model.kwargs["model"] == "gemini-2.0-flash"
    assert model.kwargs["api_key"] == "gk-test"
