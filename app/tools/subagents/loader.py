"""Subagent registry: AGENT.md definitions the agent can spawn (Upgrade 006).

An agent def is a folder under agents/ holding an AGENT.md — frontmatter (name,
description, tools = comma-separated allowlist) + body = the subagent's system
prompt. Human-authored and committed; agents only combine already-approved tools,
so there is no pending queue here (create_skill covers prompt drafting).
"""
from pathlib import Path

from app.skills.loader import _is_slug, parse_skill

# repo root: app/tools/subagents/loader.py -> parents[3] == …/argus
REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_DIR = REPO_ROOT / "agents"


def _parse_agent(path: Path) -> dict:
    """AGENT.md shares the SKILL.md format; `tools:` rides in the frontmatter."""
    meta = parse_skill(path)  # name/description/body
    tools: list[str] = []
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if line.strip().startswith("tools:"):
                    tools = [t.strip() for t in line.split(":", 1)[1].split(",")
                             if t.strip()]
    return {**meta, "tools": tools}


def list_agents() -> list[dict]:
    if not AGENTS_DIR.is_dir():
        return []
    out = []
    for md in sorted(AGENTS_DIR.glob("*/AGENT.md")):
        if md.parent.name.startswith("_"):
            continue
        try:
            out.append(_parse_agent(md))
        except OSError:
            continue
    return out


def agent_index() -> str:
    """One line per agent, for prompt injection (same shape as the skills index)."""
    return "\n".join(f"- {a['name']}: {a['description']}" for a in list_agents())


def get_agent(name: str) -> dict | None:
    if not _is_slug(name):
        return None
    md = AGENTS_DIR / name / "AGENT.md"
    return _parse_agent(md) if md.is_file() else None
