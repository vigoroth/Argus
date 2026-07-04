"""List models the user can actually select, queried live per provider."""
import os
import httpx


import re

async def list_openai_models() -> list[str]:
    """Query OpenAI for chat-capable models, collapsing dated snapshots."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return []
    EXCLUDE = ("audio", "image", "realtime", "transcribe", "tts",
               "search", "codex", "instruct", "whisper", "diarize")
    DATED = re.compile(r"-(\d{4}-\d{2}-\d{2}|\d{4})$")  # -2026-04-23 or -0125
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            r.raise_for_status()
            data = r.json().get("data", [])
        models = [
            m["id"] for m in data
            if m["id"].startswith("gpt-")
            and not any(x in m["id"] for x in EXCLUDE)
            and not DATED.search(m["id"])      # drop dated snapshots
        ]
        return sorted(set(models))
    except Exception as e:
        print(f"OpenAI model list failed: {e}")
        return []

async def list_ollama_models() -> list[str]:
    """Query local Ollama for installed models (Ollama always runs on :11434)."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://localhost:11434/api/tags")
            r.raise_for_status()
            data = r.json().get("models", [])
        return sorted(m["name"] for m in data)
    except Exception:
        return [] # Ollama not running / not installed — fine


async def list_all_models() -> dict[str, list[str]]:
    """Return {provider: [models]} for providers we can reach."""
    result = {}
    openai = await list_openai_models()
    if openai:
        result["openai"] = openai
    ollama = await list_ollama_models()
    if ollama:
        result["ollama"] = ollama
    # anthropic/gemini: add here when keys exist (their list APIs)
    return result