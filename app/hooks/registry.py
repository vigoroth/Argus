"""Hook registry (Upgrade 009) — deterministic code at fixed lifecycle points.

Tools are PULLED by the model; hooks are PUSHED by the runtime. Anything that
must happen every time — context injection, policy gates, logging — belongs
here, outside the model's control.

Events:
- "session_start"  fn(state) -> list[SystemMessage] | None      (context injection, per turn)
- "pre_tool_use"   fn(name, args) -> str | None                  (return reason -> BLOCK the call)
- "post_tool_use"  fn(name, args, result, ms) -> None            (observe; never blocks)

Hooks run in registration order. A pre_tool_use block short-circuits: later
pre-hooks still run is NOT guaranteed — first block wins. Hook exceptions are
logged and swallowed (a broken hook must not take down the turn), EXCEPT in
pre_tool_use where failing open would defeat the gate: those errors block.
"""
from collections import defaultdict

from app.core.logging_config import get_logger

log = get_logger("argus.hooks")

_HOOKS: dict[str, list] = defaultdict(list)

EVENTS = ("session_start", "pre_tool_use", "post_tool_use")


def hook(event: str):
    """Decorator: register a function for a lifecycle event."""
    if event not in EVENTS:
        raise ValueError(f"unknown hook event {event!r}; use one of {EVENTS}")

    def register(fn):
        _HOOKS[event].append(fn)
        return fn
    return register


def clear_hooks(event: str | None = None) -> None:
    """Test helper: drop registered hooks (one event or all)."""
    if event is None:
        _HOOKS.clear()
    else:
        _HOOKS.pop(event, None)


def registered(event: str) -> list:
    return list(_HOOKS.get(event, []))


def run_session_start(state) -> list:
    """Collect context messages from all session_start hooks."""
    out = []
    for fn in _HOOKS["session_start"]:
        try:
            msgs = fn(state)
            if msgs:
                out.extend(msgs)
        except Exception as e:
            log.warning("session_start hook %s failed: %s", fn.__name__, e)
    return out


def run_pre_tool_use(name: str, args: dict) -> str | None:
    """First non-None return blocks the tool call (the reason is shown to the
    model as the tool result). A crashing gate blocks too — fail closed."""
    for fn in _HOOKS["pre_tool_use"]:
        try:
            reason = fn(name, args)
        except Exception as e:
            log.warning("pre_tool_use hook %s crashed: %s — failing closed", fn.__name__, e)
            return f"policy hook {fn.__name__} errored; call blocked"
        if reason:
            return reason
    return None


def run_post_tool_use(name: str, args: dict, result: str, ms: float) -> None:
    for fn in _HOOKS["post_tool_use"]:
        try:
            fn(name, args, result, ms)
        except Exception as e:
            log.warning("post_tool_use hook %s failed: %s", fn.__name__, e)
