"""Skill tools — progressive disclosure + gated self-extension (Upgrade 004).

The agent sees only the one-line skill index in its prompt; `load_skill` pulls a
full SKILL.md body on demand. `create_skill` drafts a NEW capability into the
pending queue — it never goes live until the human approves it in the Skills tab.
"""
from langchain_core.tools import tool

from app.skills import loader


@tool
def load_skill(name: str) -> str:
    """Load the full instructions of a skill by name (see the skill index in your
    context for what's available). Use when the current task matches a skill's
    description — follow the loaded instructions.
    """
    body = loader.load_skill(name)
    if body is None:
        names = ", ".join(s["name"] for s in loader.list_skills()) or "(none)"
        return f"ERROR: no skill named {name!r}. Available: {names}"
    return body


@tool
def create_skill(name: str, description: str, body: str) -> str:
    """Draft a NEW skill when the user's task needs a reusable workflow that no
    existing skill covers. `name` is lowercase-kebab-case; `description` is the
    trigger line (say WHEN to use it); `body` is the full markdown how-to.
    The draft awaits human approval in the Skills tab — it is NOT live yet.
    """
    try:
        loader.draft_skill(name, description, body)
    except ValueError as e:
        return f"ERROR: {e}"
    except Exception as e:  # pragma: no cover — fs errors
        return f"ERROR: {e}"
    return (f"Skill '{name}' drafted — awaiting approval in the Skills tab. "
            "Tell the user to review and approve it there; it becomes loadable "
            "on their next message after approval.")


SKILL_TOOLS = [load_skill, create_skill]
