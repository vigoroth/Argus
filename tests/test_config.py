"""Settings behavior in app/core/config.py."""
from app.core import config
from app.core.config import Settings, configure_tracing


def _settings(**kwargs) -> Settings:
    # _env_file=None keeps a stray local .env out of the assertion
    return Settings(_env_file=None, **kwargs)


def test_empty_base_url_becomes_none():
    assert _settings(llm_base_url="").llm_base_url is None
    assert _settings(llm_base_url="   ").llm_base_url is None


def test_real_base_url_preserved():
    url = "http://localhost:11434/v1"
    assert _settings(llm_base_url=url).llm_base_url == url


def test_is_local_true_for_ollama():
    assert _settings(llm_provider="ollama").is_local() is True


def test_is_local_false_for_openai():
    assert _settings(llm_provider="openai").is_local() is False


def test_defaults():
    s = _settings()
    assert s.llm_model == "gpt-4o-mini"
    assert s.embed_model == "text-embedding-3-small"
    assert s.llm_temperature == 0.2
    assert s.llm_max_tokens == 1024


def test_configure_tracing_off_by_default(monkeypatch):
    monkeypatch.setattr(config, "get_settings",
                        lambda: _settings(langsmith_tracing=False))
    assert configure_tracing() is False


def test_configure_tracing_needs_key(monkeypatch):
    # tracing requested but no key → still a no-op
    monkeypatch.setattr(config, "get_settings",
                        lambda: _settings(langsmith_tracing=True, langsmith_api_key=None))
    assert configure_tracing() is False


def test_configure_tracing_exports_env(monkeypatch):
    monkeypatch.setattr(config, "get_settings", lambda: _settings(
        langsmith_tracing=True, langsmith_api_key="ls-key", langsmith_project="proj"))
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    assert configure_tracing() is True
    import os
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_API_KEY"] == "ls-key"
    assert os.environ["LANGSMITH_PROJECT"] == "proj"
