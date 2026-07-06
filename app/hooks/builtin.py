"""Built-in hooks (Upgrade 009).

session_start: the context injections that used to live inline in llm_node
(datetime, skills index, subagent index) plus the first NEW hook — calendar
reminders. pre_tool_use: the destructive-shell guardrail re-enforced at the
graph layer (defense in depth). post_tool_use: uniform tool logging.

Importing this module registers everything (graph.py imports it once).
"""
from datetime import datetime, timedelta

from langchain_core.messages import SystemMessage

from app.core.logging_config import get_logger
from app.hooks.registry import hook

log = get_logger("argus.hooks.builtin")


# ── session_start: per-turn context injection ──────────────────────────────

@hook("session_start")
def inject_datetime(state) -> list:
    """Current time, fresh each turn — relative dates ("friday 3pm") resolve."""
    return [SystemMessage(
        content="Current date/time: " + datetime.now().astimezone().isoformat())]


@hook("session_start")
def inject_skill_index(state) -> list:
    """Progressive disclosure: one line per live skill."""
    from app.skills.loader import skill_index
    idx = skill_index()
    if not idx:
        return []
    return [SystemMessage(content="Available skills (load with load_skill):\n" + idx)]


@hook("session_start")
def inject_agent_index(state) -> list:
    """Subagents the model can delegate to via spawn_agent."""
    from app.subagents.loader import agent_index
    aidx = agent_index()
    if not aidx:
        return []
    return [SystemMessage(
        content="Available subagents (delegate with spawn_agent):\n" + aidx)]


@hook("session_start")
def inject_reminders(state) -> list:
    """Upcoming calendar events (next 24h), pushed without being asked —
    the model mentions them when relevant. First genuinely NEW hook."""
    try:
        from app.calendar.store import list_events
        now = datetime.now()
        events = list_events(start=now.isoformat(timespec="minutes"),
                             end=(now + timedelta(hours=24)).isoformat(timespec="minutes"))
    except Exception as e:
        log.warning("reminder hook skipped: %s", e)
        return []
    if not events:
        return []
    lines = [f"- {e['start_ts']} {e['title']}"
             + (f" @ {e['location']}" if e.get("location") else "")
             for e in events[:5]]
    return [SystemMessage(
        content="[REMINDERS — user's next 24h. Mention when relevant, don't repeat "
                "every turn.]\n" + "\n".join(lines))]


# ── pre_tool_use: policy gates (return a reason to BLOCK) ──────────────────

@hook("pre_tool_use")
def block_destructive_shell(name: str, args: dict) -> str | None:
    """Graph-layer re-enforcement of the run_shell denylist (Upgrade 000).
    The tool checks internally too — defense in depth: this gate holds even if
    a future tool edit drops the internal check."""
    if name != "run_shell":
        return None
    from app.tools.os_tools import _is_destructive
    command = str(args.get("command", ""))
    if _is_destructive(command):
        return ("REFUSED by policy hook: destructive command pattern. "
                "Ask the user to run it manually if truly intended.")
    return None


# ── post_tool_use: observability ────────────────────────────────────────────

@hook("post_tool_use")
def log_tool_use(name: str, args: dict, result: str, ms: float) -> None:
    """Every tool call logged with duration — no trust in the model to report."""
    arg_s = " ".join(f"{k}={str(v)[:40]!r}" for k, v in list(args.items())[:3])
    log.info("tool %s(%s) -> %d chars in %.0fms", name, arg_s, len(str(result)), ms)
