"""Debounced backend watcher for safe Obsidian edits."""

from __future__ import annotations

import threading
from datetime import datetime

from app.brain.proposals import record_rejection
from app.brain.service import BrainError, _porcelain, adopt_external_edits
from app.core.config import get_settings

_STOP = threading.Event()
_THREAD: threading.Thread | None = None
_STATE = {
    "running": False,
    "last_event": None,
    "last_commit": None,
    "last_error": None,
}


def _snapshot() -> tuple[tuple[str, str], ...]:
    return tuple(_porcelain())


def _run() -> None:
    _STATE["running"] = True
    prior: tuple[tuple[str, str], ...] = ()
    stable = 0
    interval = max(0.5, get_settings().argus_brain_watch_interval)
    try:
        while not _STOP.wait(interval):
            current = _snapshot()
            if not current:
                prior, stable = (), 0
                continue
            stable = stable + 1 if current == prior else 0
            prior = current
            if stable < 1:
                continue
            _STATE["last_event"] = datetime.now().astimezone().isoformat()
            try:
                receipt = adopt_external_edits()
                _STATE["last_commit"] = receipt["commit"] if receipt else None
                _STATE["last_error"] = None
            except BrainError as exc:
                _STATE["last_error"] = str(exc)
                record_rejection("obsidian-watcher", str(exc))
            prior, stable = (), 0
    finally:
        _STATE["running"] = False


def start_watcher() -> None:
    global _THREAD
    if not get_settings().argus_brain_watch or (_THREAD and _THREAD.is_alive()):
        return
    _STOP.clear()
    _THREAD = threading.Thread(target=_run, name="argus-brain-watcher", daemon=True)
    _THREAD.start()


def stop_watcher(timeout: float = 5.0) -> None:
    _STOP.set()
    if _THREAD:
        _THREAD.join(timeout=timeout)


def watcher_status() -> dict:
    return dict(_STATE)
