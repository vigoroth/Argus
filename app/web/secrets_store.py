"""Encrypted, at-rest storage for provider API keys, so keys can be set at runtime
from the login-gated dashboard instead of only via .env.

Keys are encrypted with Fernet before hitting Postgres. The Fernet key is derived
from ARGUS_SESSION_SECRET (already required at boot) — no new managed secret. Note:
rotating ARGUS_SESSION_SECRET makes existing ciphertext undecryptable; keys can just
be re-entered from the dashboard.

The dashboard is write-only: values are never returned over the API — only whether a
provider has a key set. On write (and at startup) apply_secrets() pushes decrypted keys
into BOTH read paths (os.environ + the cached Settings) and clears the graph cache so
running code picks up the change without a restart.
"""
import base64
import hashlib
import os

import psycopg
from cryptography.fernet import Fernet

from app.core.config import get_settings

# provider -> (env var read by models_list.py / subprocesses, Settings field read by llm.py)
PROVIDERS = {
    "openai": ("OPENAI_API_KEY", "openai_api_key"),
    "anthropic": ("ANTHROPIC_API_KEY", "anthropic_api_key"),
    "google": ("GOOGLE_API_KEY", "google_api_key"),
}


def _conn():
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(url)


def _fernet() -> Fernet:
    """Derive a stable Fernet key from the session secret."""
    secret = os.environ.get("ARGUS_SESSION_SECRET") or os.environ.get("NEXUS_SESSION_SECRET", "")
    digest = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def init_secrets_table() -> None:
    """Create the secrets table if it doesn't exist."""
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS secrets ("
            "provider TEXT PRIMARY KEY, "
            "ciphertext BYTEA NOT NULL, "
            "updated_at TIMESTAMPTZ DEFAULT now())"
        )


def set_secret(provider: str, plaintext: str) -> None:
    """Encrypt and upsert one provider's key."""
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider: {provider}")
    ciphertext = _fernet().encrypt(plaintext.encode())
    with _conn() as conn:
        conn.execute(
            "INSERT INTO secrets (provider, ciphertext, updated_at) VALUES (%s, %s, now()) "
            "ON CONFLICT (provider) DO UPDATE SET ciphertext = EXCLUDED.ciphertext, "
            "updated_at = now()",
            (provider, ciphertext),
        )


def _all_secrets() -> dict[str, str]:
    """Decrypt every stored key. Server-side only — never exposed over the API."""
    out: dict[str, str] = {}
    with _conn() as conn:
        rows = conn.execute("SELECT provider, ciphertext FROM secrets").fetchall()
    for provider, ciphertext in rows:
        try:
            out[provider] = _fernet().decrypt(bytes(ciphertext)).decode()
        except Exception:
            continue  # unreadable (e.g. session secret rotated) — skip
    return out


def secret_status() -> dict[str, bool]:
    """Which providers currently have a key set (presence only — write-only API)."""
    stored = set(_all_secrets())
    return {p: p in stored for p in PROVIDERS}


def apply_secrets(graphs_cache: dict | None = None) -> None:
    """Push stored keys into both read paths so running code uses them without a
    restart: os.environ (models_list.py, vault subprocess) AND the lru-cached Settings
    instance (llm.py). Then clear the compiled-graph cache so new graphs rebind."""
    secrets = _all_secrets()
    settings = get_settings()
    for provider, plaintext in secrets.items():
        env_name, field = PROVIDERS[provider]
        os.environ[env_name] = plaintext
        setattr(settings, field, plaintext)
    if graphs_cache is not None:
        graphs_cache.clear()
