"""Upload store for the data-analyst (Upgrade 010).

Files land in data/uploads/ (gitignored with the rest of data/). Filenames are
sanitized to a strict allowlist — the stored name is what gets handed to the
analyst as a path, so it must never traverse.
"""
import re
from pathlib import Path

# repo root: app/web/uploads.py -> parents[2] == …/argus
REPO_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_DIR = REPO_ROOT / "data" / "uploads"

MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB
ALLOWED_EXT = {".csv", ".tsv", ".txt", ".json", ".xlsx", ".xls", ".parquet",
               ".sqlite", ".db"}

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str) -> str:
    """Basename only, allowlisted chars, no leading dots, capped length."""
    base = Path(name).name  # drops any path components
    base = _SAFE.sub("_", base).lstrip(".")
    return base[:120] or "upload"


def allowed(name: str) -> bool:
    return Path(name).suffix.lower() in ALLOWED_EXT


def save_upload(name: str, data: bytes) -> Path:
    """Store bytes under a sanitized, collision-free name; return the path."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    fname = safe_filename(name)
    dest = UPLOADS_DIR / fname
    stem, suffix = dest.stem, dest.suffix
    n = 1
    while dest.exists():  # never overwrite an earlier upload
        dest = UPLOADS_DIR / f"{stem}_{n}{suffix}"
        n += 1
    dest.write_bytes(data)
    return dest


def list_uploads() -> list[dict]:
    if not UPLOADS_DIR.is_dir():
        return []
    out = []
    for p in sorted(UPLOADS_DIR.iterdir()):
        if p.is_file():
            st = p.stat()
            out.append({"name": p.name, "size": st.st_size, "mtime": int(st.st_mtime)})
    return out


def delete_upload(name: str) -> bool:
    fname = safe_filename(name)
    p = UPLOADS_DIR / fname
    if not p.is_file():
        return False
    p.unlink()
    return True
