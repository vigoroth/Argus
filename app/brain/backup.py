"""Explicit local backup and recovery validation for the nested Brain Git repo."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from app.brain import service
from app.brain.service import BrainError


def create_bundle(destination: str | None = None) -> dict:
    if service._status_paths():
        raise BrainError("brain must be clean before backup")
    backup_dir = Path(destination or "data/brain_backups").expanduser().resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    bundle = backup_dir / f"second-brain-{datetime.now():%Y%m%d-%H%M%S}.bundle"
    proc = subprocess.run(
        ["git", "-C", str(service.brain_root()), "bundle", "create", str(bundle), "--all"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode:
        raise BrainError((proc.stderr or proc.stdout).strip())
    validation = validate_bundle(str(bundle))
    return {"path": str(bundle), "head": service._head(), "validation": validation}


def validate_bundle(bundle_path: str) -> dict:
    bundle = Path(bundle_path).expanduser().resolve()
    if not bundle.is_file():
        raise BrainError("backup bundle not found")
    verify = subprocess.run(
        ["git", "bundle", "verify", str(bundle)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if verify.returncode:
        raise BrainError((verify.stderr or verify.stdout).strip())
    temp = Path(tempfile.mkdtemp(prefix="argus-brain-restore-"))
    try:
        clone = subprocess.run(
            ["git", "clone", "--quiet", str(bundle), str(temp / "brain")],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if clone.returncode:
            raise BrainError((clone.stderr or clone.stdout).strip())
        restored = subprocess.run(
            ["git", "-C", str(temp / "brain"), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return {"valid": True, "restored_head": restored}
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def remote_status() -> dict:
    remotes = service._git("remote", "-v", check=False).splitlines()
    return {"configured": bool(remotes), "remotes": remotes}
