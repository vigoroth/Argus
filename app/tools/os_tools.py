import re
import subprocess
from pathlib import Path

from langchain_core.tools import tool

# Guardrail (NOT a sandbox): refuse obviously destructive commands before running.
# run_shell is LLM-driven with shell=True, so a hallucinated or injected command
# could wreck the host. This blocks the classic footguns; it is defense-in-depth
# on top of the localhost-only bind + login gate, not a security boundary. The
# user's own /term shell is intentionally unrestricted.
_DESTRUCTIVE_PATTERNS = [
    r"\brm\s+(-[a-z]*\s+)*(-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r)\b",  # rm -rf / rm -fr
    r"\bmkfs\b",                       # format a filesystem
    r"\bdd\b[^\n]*\bof=/dev/",         # dd onto a raw device
    r">\s*/dev/(sd|nvme|hd|vd)",       # clobber a disk device
    r"\b(shutdown|reboot|halt|poweroff|init\s+0|init\s+6)\b",
    r":\(\)\s*\{.*\}\s*;",             # fork bomb  :(){ :|:& };:
    r"\bchmod\s+-R\s+000\s+/",         # brick permissions from root
    r"/dev/(sd|nvme|hd|vd)[a-z0-9]*\s",
]
_DENY_RE = re.compile("|".join(_DESTRUCTIVE_PATTERNS), re.IGNORECASE)


def _is_destructive(command: str) -> bool:
    return bool(_DENY_RE.search(command))


@tool
def read_file(path: str) -> str:
    """Read and return the full text content of a file."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: {e}"
    

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file, creating it if it does not exist.
    Use this to save output, create new files, or overwrite existing ones.
    """

    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"OK: wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing file {path}: {e}"
    

@tool
def list_dir(path :str) -> str:
    """List files and directories at the given path.
    Use this to explore what files exist before reading or writing.
    """
    try:
        entries = sorted(Path(path).iterdir())
        lines = []
        for e in entries:
            kind = "DIR" if e.is_dir() else "FILE"
            lines.append(f"{kind:4} {e.name}")
        return "\n".join(lines) if lines else f"No entries in {path}"
    except Exception as e:
        return f"Error listing directory {path}: {e}"

@tool
def run_shell(command: str) -> str:
    """Run a shell command and return its stdout and stderr.
    Use for tasks like counting lines, searching files, or running scripts.
    NEVER run destructive commands like rm -rf.
    """
    if _is_destructive(command):
        return ("REFUSED: this command matches a destructive-command guardrail "
                "(e.g. rm -rf, mkfs, dd to a device, shutdown, fork bomb) and was "
                "not run. Rephrase to a safe, specific, non-destructive command.")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 30 seconds"
    except Exception as e:
        return f"ERROR: {e}"

# Full catalog of filesystem tools. The agent loop (app.agent.graph) binds only
# read_file, list_dir, and run_shell — write_file is intentionally NOT given to the
# model (run_shell already covers writes; keeping write_file unbound shrinks the
# blast radius). write_file remains here for the CLI demo / explicit use.
OS_TOOLS = [read_file, write_file, list_dir, run_shell]