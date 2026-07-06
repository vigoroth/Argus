"""Model manager: name validation + pull-stream behavior without a live Ollama."""
import pytest

from app.web.model_manager import pull_model_events, valid_model_name


def test_valid_names():
    for n in ("llama3.2:3b", "qwen3:8b", "mistral", "gpt-oss:20b",
              "hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:Q4_K_M",
              "org/repo", "a1"):
        assert valid_model_name(n), n


def test_invalid_names():
    for n in ("", " ", "name with spaces", "../etc/passwd", "a;rm -rf /",
              "name\n", "-leading-dash", "a" * 201, "a|b", "$(x)"):
        assert not valid_model_name(n), repr(n)


@pytest.mark.asyncio
async def test_pull_unreachable_ollama_yields_error(monkeypatch):
    """No Ollama on the patched port → a clean error event, no exception."""
    from app.web import model_manager
    monkeypatch.setattr(model_manager, "OLLAMA", "http://localhost:1")  # nothing listens
    events = [ev async for ev in pull_model_events("llama3.2:3b")]
    assert len(events) == 1
    assert "error" in events[0]
