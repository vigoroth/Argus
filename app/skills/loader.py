"""Skill store: loadable SKILL.md capabilities with progressive disclosure.

A skill is a folder under skills/ holding a SKILL.md — frontmatter (name,
description) + a markdown body. The agent's prompt carries only the one-line
descriptions (the index); the full body is pulled on demand via the load_skill
tool. Agent-drafted skills land in skills/_pending/ and only go live after a
human approves them in the Skills tab (capability firewall).
"""
import re
import shutil
from pathlib import Path

# repo root: app/skills/loader.py -> parents[2] == …/argus
REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"
PENDING_DIR = SKILLS_DIR / "_pending"

_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")  # path-traversal guard for names


def _is_slug(name: str) -> bool:
    return bool(_SLUG.match(name))


def parse_skill(path: Path) -> dict:
    """Parse a SKILL.md: minimal ----fenced frontmatter (name, description) + body."""
    text = path.read_text(encoding="utf-8")
    meta = {"name": path.parent.name, "description": ""}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    if k.strip() in ("name", "description"):
                        meta[k.strip()] = v.strip()
            body = parts[2].lstrip("\n")
    return {**meta, "body": body, "path": str(path)}


def _scan(root: Path) -> list[dict]:
    if not root.is_dir():
        return []
    out = []
    for md in sorted(root.glob("*/SKILL.md")):
        if md.parent.name.startswith("_"):
            continue  # _pending and friends are not live
        try:
            out.append(parse_skill(md))
        except OSError:
            continue
    return out


def list_skills() -> list[dict]:
    """Live skills only."""
    return _scan(SKILLS_DIR)


def list_pending() -> list[dict]:
    """Agent drafts awaiting human approval (bodies included for review)."""
    if not PENDING_DIR.is_dir():
        return []
    return [parse_skill(md) for md in sorted(PENDING_DIR.glob("*/SKILL.md"))]


def skill_index() -> str:
    """One line per live skill — this is all the system prompt carries."""
    return "\n".join(f"- {s['name']}: {s['description']}" for s in list_skills())


def load_skill(name: str) -> str | None:
    """Full body of a live skill, or None."""
    if not _is_slug(name):
        return None
    md = SKILLS_DIR / name / "SKILL.md"
    return parse_skill(md)["body"] if md.is_file() else None


def draft_skill(name: str, description: str, body: str) -> Path:
    """Write an agent-proposed skill to _pending/ — never live until approved."""
    if not _is_slug(name):
        raise ValueError(f"invalid skill name {name!r}: use lowercase-kebab-case")
    if (SKILLS_DIR / name / "SKILL.md").exists():
        raise ValueError(f"skill {name!r} already exists")
    dest = PENDING_DIR / name
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body.strip()}\n",
        encoding="utf-8",
    )
    return dest / "SKILL.md"


def approve_skill(name: str) -> bool:
    """Promote a pending draft to live. False if no such draft."""
    if not _is_slug(name):
        return False
    src, dst = PENDING_DIR / name, SKILLS_DIR / name
    if not (src / "SKILL.md").is_file() or dst.exists():
        return False
    shutil.move(str(src), str(dst))
    return True


def reject_skill(name: str) -> bool:
    """Delete a pending draft. False if no such draft."""
    if not _is_slug(name):
        return False
    src = PENDING_DIR / name
    if not (src / "SKILL.md").is_file():
        return False
    shutil.rmtree(src)
    return True
