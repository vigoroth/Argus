"""Write Nexus conversations to an Obsidian vault as markdown notes.
Each conversation becomes one .md file; Obsidian's graph view visualizes them,
and graphify builds a queryable knowledge graph over the same vault.
"""
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

from app.core.config import get_settings

VAULT_PATH = Path(get_settings().nexus_vault_path)
CONV_DIR = VAULT_PATH / "Conversations"

# debounce state for graph refresh: one extract at a time, min spacing
_extract_proc: subprocess.Popen | None = None
_last_extract_ts: float = 0.0
_MIN_EXTRACT_INTERVAL_S = 120


def _safe_filename(title: str) -> str:
    """Turn a conversation title into a safe .md filename."""
    name = re.sub(r'[^\w\s-]', '', title).strip()[:60] or "untitled"
    return name


def write_conversation(conv_id: str, title: str, messages: list[dict]) -> None:
    """Write/overwrite a conversation as a markdown note in the vault.
    messages: list of {role, content}.
    """
    try:
        CONV_DIR.mkdir(parents=True, exist_ok=True)
        fname = f"{_safe_filename(title)}.md"
        path = CONV_DIR / fname

        lines = [f"# {title}", f"*{datetime.now():%Y-%m-%d %H:%M}*", ""]
        for m in messages:
            who = "You" if m["role"] == "user" else "Nexus"
            lines.append(f"**{who}:** {m['content']}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
    except Exception as e:
        print(f"vault write failed: {e}")  # don't break chat if vault write fails


def refresh_graph(vault_path: Path = VAULT_PATH) -> None:
    """Rebuild the graphify knowledge graph over the vault, best-effort and
    non-blocking. Full `extract` so new conversation markdown is semantically
    re-indexed (LLM-backed). Debounced: skip if a previous extract is still
    running or one finished less than _MIN_EXTRACT_INTERVAL_S ago — extracts
    must never pile up and eat the machine.
    The subprocess inherits the app's env (OPENAI_API_KEY from .env).
    """
    global _extract_proc, _last_extract_ts
    graphify = shutil.which("graphify")
    if not graphify:
        print("graph refresh skipped: graphify not on PATH")
        return
    if _extract_proc is not None and _extract_proc.poll() is None:
        return  # previous extract still running
    import time
    if time.monotonic() - _last_extract_ts < _MIN_EXTRACT_INTERVAL_S:
        return  # too soon since the last one
    # pin the extract backend to the app's LLM provider — graphify's auto-detect
    # picks any backend with an env key set, even an invalid one (a stale
    # GOOGLE_API_KEY silently selects gemini and every extract fails unseen)
    backend = {"openai": "openai", "anthropic": "claude",
               "google": "gemini", "ollama": "ollama"}.get(get_settings().llm_provider)
    cmd = [graphify, "extract", str(vault_path)]
    if backend:
        cmd += ["--backend", backend]
    try:
        # detached, output discarded — do not wait
        _extract_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(vault_path),
        )
        _last_extract_ts = time.monotonic()
    except Exception as e:
        print(f"graph refresh skipped: {e}")  # never break chat on graph refresh


def graph_build_status() -> str:
    """'building' while an extract subprocess is running, else 'idle'."""
    if _extract_proc is not None and _extract_proc.poll() is None:
        return "building"
    return "idle"