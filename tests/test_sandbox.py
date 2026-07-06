"""Sandboxed run_shell (Upgrade 011): real isolation properties, probed live.

Skips wholesale where bubblewrap can't run (CI runners without userns) — the
fail-soft plain-subprocess path keeps behavior identical there.
"""
import subprocess

import pytest

from app.core import sandbox
from app.core.sandbox import DATA_DIR, REPO_ROOT, run_sandboxed, sandbox_backend


def _bwrap_usable() -> bool:
    if sandbox_backend() != "bwrap":
        return False
    try:  # probe: userns may be blocked even when the binary exists
        r = subprocess.run(sandbox._bwrap_argv("true"), capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _bwrap_usable(),
                                reason="bwrap not usable on this host")


def test_basic_execution():
    assert run_sandboxed("echo hello").strip() == "hello"


def test_host_readable():
    # host env (python + libs) visible read-only — analysis keeps working
    out = run_sandboxed("python3 -c 'print(6*7)'")
    assert "42" in out


def test_repo_readonly():
    out = run_sandboxed(f"touch {REPO_ROOT}/pwned.txt")
    assert "Read-only" in out or "read-only" in out
    assert not (REPO_ROOT / "pwned.txt").exists()


def test_data_dir_writable():
    probe = DATA_DIR / "sandbox_probe.txt"
    out = run_sandboxed(f"echo ok > {probe} && cat {probe}")
    try:
        assert "ok" in out
        assert (DATA_DIR / "sandbox_probe.txt").exists()  # visible on the host
    finally:
        (DATA_DIR / "sandbox_probe.txt").unlink(missing_ok=True)


def test_tmp_writable_but_ephemeral():
    assert "ok" in run_sandboxed("echo ok > /tmp/x && cat /tmp/x")
    # fresh tmpfs per call: the file from the previous call is gone
    assert "ok" not in run_sandboxed("cat /tmp/x 2>&1")


def test_network_blocked():
    # success marker is assembled at runtime so the traceback echoing the
    # source line can't contain it
    out = run_sandboxed(
        "python3 -c \"import socket; s=socket.socket(); s.settimeout(3); "
        "s.connect(('1.1.1.1', 80)); print('CONN'+'ECTED')\" 2>&1")
    assert "CONNECTED" not in out
    assert "unreachable" in out.lower() or "timed out" in out.lower()


def test_timeout(monkeypatch):
    monkeypatch.setattr(sandbox, "TIMEOUT_S", 2)
    assert "timed out" in run_sandboxed("sleep 10")


def test_env_off_switch(monkeypatch):
    monkeypatch.setenv("ARGUS_SANDBOX", "off")
    assert sandbox_backend() == "none"
