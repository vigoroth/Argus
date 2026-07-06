"""Gated tool creation — the executable half of self-extension (Upgrade 006).

create_tool drafts Python source into app/tools/custom/_pending/. A human reads
the code in the Skills tab and approves (move into custom/) or rejects (delete).
Only approved files are ever imported; load_custom_tools() scans custom/*.py and
collects each module's TOOLS list at graph build time. The firewall for skills
was about instructions — this one is about code, so the human review happens
BEFORE the first import.
"""
import importlib.util
from pathlib import Path

from app.core.logging_config import get_logger
from app.skills.loader import _is_slug

log = get_logger("argus.skills.toolgate")

# repo root: app/skills/toolgate.py -> parents[2] == …/argus
REPO_ROOT = Path(__file__).resolve().parents[2]
CUSTOM_DIR = REPO_ROOT / "app" / "tools" / "custom"
PENDING_TOOLS_DIR = CUSTOM_DIR / "_pending"


def draft_tool(name: str, code: str) -> Path:
    """Write agent-proposed tool source to the pending queue (inert until approved)."""
    if not _is_slug(name):
        raise ValueError(f"invalid tool name {name!r}: use lowercase-kebab-case")
    mod = name.replace("-", "_")
    if (CUSTOM_DIR / f"{mod}.py").exists():
        raise ValueError(f"custom tool {name!r} already exists")
    if "TOOLS" not in code:
        raise ValueError("tool code must define a module-level TOOLS = [...] list")
    PENDING_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    dest = PENDING_TOOLS_DIR / f"{mod}.py"
    dest.write_text(code, encoding="utf-8")
    return dest


def list_pending_tools() -> list[dict]:
    """Pending drafts with full source, for human review in the UI."""
    if not PENDING_TOOLS_DIR.is_dir():
        return []
    return [{"name": p.stem.replace("_", "-"), "code": p.read_text(encoding="utf-8")}
            for p in sorted(PENDING_TOOLS_DIR.glob("*.py"))]


def approve_tool(name: str) -> bool:
    """Promote a pending draft into custom/ (imported on next graph build)."""
    if not _is_slug(name):
        return False
    mod = name.replace("-", "_")
    src, dst = PENDING_TOOLS_DIR / f"{mod}.py", CUSTOM_DIR / f"{mod}.py"
    if not src.is_file() or dst.exists():
        return False
    src.rename(dst)
    return True


def reject_tool(name: str) -> bool:
    if not _is_slug(name):
        return False
    src = PENDING_TOOLS_DIR / (name.replace("-", "_") + ".py")
    if not src.is_file():
        return False
    src.unlink()
    return True


def load_custom_tools() -> list:
    """Import every APPROVED custom module and collect its TOOLS. _pending/ is
    never scanned. A broken module is skipped with a warning, not fatal."""
    out = []
    if not CUSTOM_DIR.is_dir():
        return out
    for p in sorted(CUSTOM_DIR.glob("*.py")):
        if p.stem.startswith("_"):
            continue  # __init__ and any _-prefixed helpers
        try:
            spec = importlib.util.spec_from_file_location(f"app.tools.custom.{p.stem}", p)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            tools = getattr(module, "TOOLS", [])
            out.extend(tools)
            if tools:
                log.info("loaded custom tool module %s (%d tool[s])", p.stem, len(tools))
        except Exception as e:
            log.warning("custom tool module %s failed to load: %s", p.stem, e)
    return out
