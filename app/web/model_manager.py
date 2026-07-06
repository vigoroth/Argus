"""Local model management via the Ollama HTTP API (Upgrade 008).

Pulling goes through Ollama's own registry client, which also handles Hugging
Face GGUFs natively: `hf.co/<org>/<repo>:<quant>` is a valid model name. We
never shell out — POST /api/pull streams NDJSON progress that we re-emit as SSE.
"""
import json
import re

import httpx

from app.core.logging_config import get_logger

log = get_logger("argus.web.model_manager")

OLLAMA = "http://localhost:11434"

# ollama and hf.co model names: org/repo:tag with dots/dashes/underscores.
# Allowlist via fullmatch ($ would accept a trailing newline) — this string
# reaches the Ollama API, never a shell.
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\-]*(/[A-Za-z0-9._\-]+)*(:[A-Za-z0-9._\-]+)?")


def valid_model_name(name: str) -> bool:
    return bool(name) and len(name) <= 200 and bool(_NAME.fullmatch(name))


async def pull_model_events(name: str):
    """Async generator: Ollama pull progress as dicts.

    Yields {"status": ..., "completed": int, "total": int} lines; terminates
    with {"status": "success"} or {"error": ...}. Never raises — errors become
    an error event so the SSE stream closes cleanly.
    """
    # connect fails fast; read stays unlimited — model downloads run for minutes
    timeout = httpx.Timeout(connect=5, read=None, write=30, pool=5)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", f"{OLLAMA}/api/pull",
                json={"model": name, "stream": True},
            ) as r:
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
    except (httpx.ConnectError, httpx.ConnectTimeout):
        yield {"error": "Ollama is not running on localhost:11434."}
    except Exception as e:  # network blips mid-download etc.
        log.warning("model pull %r failed: %s", name, e)
        yield {"error": str(e)}


async def delete_model(name: str) -> bool:
    """Remove a local model. True if Ollama deleted it."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.request("DELETE", f"{OLLAMA}/api/delete",
                                     json={"model": name})
            return r.status_code == 200
    except Exception as e:
        log.warning("model delete %r failed: %s", name, e)
        return False
