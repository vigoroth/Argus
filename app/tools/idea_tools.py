"""Idea tools — let the agent push brainstormed upgrades into the lab backlog
(Upgrade 005). lab/IDEAS.md is a private local file; appending rows there is the
whole pipeline: brainstorm skill → add_idea → next `lab.py` cycle picks them up.
"""
import re
from pathlib import Path

from langchain_core.tools import tool

# repo root: app/tools/idea_tools.py -> parents[2] == …/argus
REPO_ROOT = Path(__file__).resolve().parents[2]
IDEAS_MD = REPO_ROOT / "lab" / "IDEAS.md"

_EFFORT = {"small": "🟢", "medium": "🟡", "large": "🔴"}
CATEGORIES = ("ml", "systems", "security", "frontend", "devops", "agent", "rag", "perf")


@tool
def add_idea(idea: str, category: str, why: str, effort: str = "medium") -> str:
    """Record an upgrade idea in the project's private backlog (lab/IDEAS.md).
    Use after a brainstorm, once the user accepts an idea.
    `category`: one of ml/systems/security/frontend/devops/agent/rag/perf.
    `effort`: small, medium, or large.
    """
    if not IDEAS_MD.is_file():
        return "ERROR: lab/IDEAS.md not found — the lab backlog is missing."
    cat = category.strip().lower()
    if cat not in CATEGORIES:
        return f"ERROR: category must be one of {', '.join(CATEGORIES)}."
    badge = _EFFORT.get(effort.strip().lower(), "🟡")
    clean = lambda s: " ".join(str(s).split()).replace("|", "/")  # noqa: E731 — keep the table intact
    row = f"| {clean(idea)} | {cat} | {clean(why)} | {badge} | idea |"

    text = IDEAS_MD.read_text(encoding="utf-8")
    # append after the LAST row of the ideas table (lines starting with '|')
    rows = [m.end() for m in re.finditer(r"(?m)^\|.*\|\s*$", text)]
    if not rows:
        return "ERROR: no ideas table found in lab/IDEAS.md."
    pos = rows[-1]
    IDEAS_MD.write_text(text[:pos] + "\n" + row + text[pos:], encoding="utf-8")
    return f"Idea recorded in the lab backlog: {clean(idea)} [{cat}, {badge}]"


IDEA_TOOLS = [add_idea]
