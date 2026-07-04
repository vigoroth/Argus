import psycopg
from app.core.config import get_settings


def _conn():
    # psycopg wants a plain postgresql:// URL, not the +psycopg variant
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(url)


def init_memory_table() -> None:
    """Create the long-term memory table if it doesn't exist."""
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS user_memory ("
            "key TEXT PRIMARY KEY, "
            "value TEXT NOT NULL, "
            "updated_at TIMESTAMPTZ DEFAULT now())"
        )


def remember(key: str, value: str) -> None:
    """Store or update a durable fact. Upsert on key."""
    with _conn() as conn:
        conn.execute(
            "INSERT INTO user_memory (key, value) VALUES (%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()",
            (key, value),
        )


def recall_all() -> dict[str, str]:
    """Return all stored facts as a dict."""
    with _conn() as conn:
        rows = conn.execute("SELECT key, value FROM user_memory ORDER BY updated_at DESC").fetchall()
    return {k: v for k, v in rows}