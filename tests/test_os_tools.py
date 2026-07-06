"""Destructive-command guardrail for the LLM-driven run_shell tool.

This is defense-in-depth (not a sandbox); these tests lock in the classic
footguns it must refuse and confirm benign commands are unaffected.
"""
import pytest

from app.tools.os_tools import _is_destructive, run_shell

DESTRUCTIVE = [
    "rm -rf /",
    "rm -fr ~/project",
    "sudo rm -rf /var/lib",
    "mkfs.ext4 /dev/sda1",
    "dd if=/dev/zero of=/dev/sda",
    "shutdown now",
    "reboot",
    "poweroff",
    ":(){ :|:& };:",
]

BENIGN = [
    "wc -l README.md",
    "ls -la",
    "grep -r rm .",       # 'rm' as a substring, not the command
    "echo remove this",
    "git rm stale.txt",   # git rm is not a filesystem wipe
    "python -m pytest -q",
]


@pytest.mark.parametrize("cmd", DESTRUCTIVE)
def test_destructive_flagged(cmd):
    assert _is_destructive(cmd) is True


@pytest.mark.parametrize("cmd", BENIGN)
def test_benign_allowed(cmd):
    assert _is_destructive(cmd) is False


def test_run_shell_refuses_destructive_without_executing():
    out = run_shell.invoke({"command": "rm -rf /tmp/should_not_run"})
    assert out.startswith("REFUSED")


def test_run_shell_runs_benign():
    out = run_shell.invoke({"command": "echo hello"})
    assert "hello" in out
