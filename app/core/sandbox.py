"""Sandboxed shell execution (Upgrade 011) — real isolation for run_shell.

Backend: bubblewrap (bwrap) user namespaces. The command sees the host
filesystem READ-ONLY (so python/pandas/conda all work), with exactly two
writable places: the repo's data/ directory and a fresh tmpfs /tmp. No
network, no view of host processes, dies with the parent.

This replaces "regex denylist as the only line" with an actual boundary:
  - writes outside data/ and /tmp fail with EROFS (the repo code itself is RO)
  - network egress is gone (no exfil, no surprise downloads)
  - the process tree is namespaced (can't signal host processes)
The denylist stays as a cheap first filter; the sandbox is the enforcement.

Fail-soft: if bwrap is unavailable (or ARGUS_SANDBOX=off), fall back to the
plain subprocess with a log warning — same behavior as pre-011.
"""
import os
import shutil
import subprocess
from pathlib import Path

from app.core.logging_config import get_logger

log = get_logger("argus.core.sandbox")

# repo root: app/core/sandbox.py -> parents[2] == …/argus
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"

TIMEOUT_S = 30
MAX_OUTPUT = 20_000  # chars returned to the model


def sandbox_backend() -> str:
    """'bwrap' when usable, else 'none'. ARGUS_SANDBOX=off forces plain mode."""
    if os.environ.get("ARGUS_SANDBOX", "").lower() in ("off", "0", "none"):
        return "none"
    if shutil.which("bwrap"):
        return "bwrap"
    return "none"


def _bwrap_argv(command: str) -> list[str]:
    DATA_DIR.mkdir(exist_ok=True)
    return [
        "bwrap",
        "--ro-bind", "/", "/",              # whole host visible, read-only
        "--bind", str(DATA_DIR), str(DATA_DIR),  # the ONE writable project dir
        "--tmpfs", "/tmp",                  # scratch, discarded after the call
        "--proc", "/proc",
        "--dev", "/dev",
        "--unshare-all",                    # net, pid, ipc, uts, cgroup, user
        "--die-with-parent",
        "--chdir", str(REPO_ROOT),
        "bash", "-c", command,
    ]


def run_sandboxed(command: str) -> str:
    """Execute `command`, sandboxed when possible. Returns combined output text."""
    backend = sandbox_backend()
    if backend == "bwrap":
        argv: list[str] | str = _bwrap_argv(command)
        shell = False
    else:
        log.warning("sandbox unavailable — running run_shell UNSANDBOXED")
        argv, shell = command, True

    try:
        result = subprocess.run(
            argv, shell=shell, capture_output=True, text=True, timeout=TIMEOUT_S,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {TIMEOUT_S} seconds"
    except Exception as e:
        return f"ERROR: {e}"

    output = result.stdout
    if result.stderr:
        output += f"\nSTDERR: {result.stderr}"
    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT] + f"\n…(truncated at {MAX_OUTPUT} chars)"
    return output or "(no output)"
