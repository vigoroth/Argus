import time
from contextlib import contextmanager

import psycopg

from app.core.config import get_settings


def _conn():
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(url)


def init_metrics_table() -> None:
    """Create the run_metrics table if it doesn't exist."""
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS run_metrics ("
            "id SERIAL PRIMARY KEY, "
            "ts TIMESTAMPTZ DEFAULT now(), "
            "label TEXT, "
            "duration_ms DOUBLE PRECISION, "
            "input_tokens INTEGER, "
            "output_tokens INTEGER, "
            "cost_usd DOUBLE PRECISION, "
            "success BOOLEAN, "
            "error TEXT)"
        )
        # web-chat metrics link runs to a conversation + the model used
        conn.execute("ALTER TABLE run_metrics ADD COLUMN IF NOT EXISTS conversation_id TEXT")
        conn.execute("ALTER TABLE run_metrics ADD COLUMN IF NOT EXISTS model TEXT")


def init_activity_table() -> None:
    """Create the activity_events table (one row per tool call / result), so the
    per-conversation activity log survives a page reload."""
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS activity_events ("
            "id SERIAL PRIMARY KEY, "
            "conversation_id TEXT, "
            "ts TIMESTAMPTZ DEFAULT now(), "
            "kind TEXT, "
            "text TEXT)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_conv "
            "ON activity_events (conversation_id, id)"
        )


def record_activity(conversation_id: str, entries: list[dict]) -> None:
    """Persist one turn's activity events (each {'kind','text'}) for a conversation."""
    if not entries:
        return
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO activity_events (conversation_id, kind, text) "
                "VALUES (%s, %s, %s)",
                [(conversation_id, e.get("kind", "info"), e.get("text", "")) for e in entries],
            )


def get_activity(conversation_id: str) -> list[dict]:
    """Return a conversation's activity events, oldest first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT kind, text, ts FROM activity_events "
            "WHERE conversation_id = %s ORDER BY id",
            (conversation_id,),
        ).fetchall()
    return [{"kind": r[0], "text": r[1], "ts": str(r[2])} for r in rows]


def record_run(label, duration_ms, input_tokens, output_tokens, cost_usd, success,
               error=None, conversation_id=None, model=None):
    """Write one run's metrics to Postgres."""
    with _conn() as conn:
        conn.execute(
            "INSERT INTO run_metrics "
            "(label, duration_ms, input_tokens, output_tokens, cost_usd, success, error, "
            " conversation_id, model) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (label, duration_ms, input_tokens, output_tokens, cost_usd, success, error,
             conversation_id, model),
        )


def get_stats_summary() -> dict:
    """Totals, 14-day daily series, and the last 20 chat runs — one round trip
    via json_agg/row_to_json instead of three separate queries."""
    with _conn() as conn:
        row = conn.execute(
            "WITH t AS ("
            "  SELECT COUNT(*) runs, "
            "         COALESCE(AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END), 0) success_rate, "
            "         COALESCE(AVG(duration_ms), 0) avg_ms, "
            "         COALESCE(percentile_cont(0.95) WITHIN GROUP "
            "(ORDER BY duration_ms), 0) p95_ms, "
            "         COALESCE(SUM(input_tokens), 0) input_tokens, "
            "         COALESCE(SUM(output_tokens), 0) output_tokens, "
            "         COALESCE(SUM(cost_usd), 0) cost_usd "
            "  FROM run_metrics WHERE label = 'chat'"
            "), d AS ("
            "  SELECT date_trunc('day', ts)::date::text AS day, COUNT(*) runs, "
            "         COALESCE(SUM(cost_usd), 0) cost, COALESCE(AVG(duration_ms), 0) avg_ms "
            "  FROM run_metrics WHERE label = 'chat' AND ts > now() - interval '14 days' "
            "  GROUP BY 1 ORDER BY 1"
            "), r AS ("
            "  SELECT to_char(ts, 'MM-DD HH24:MI') AS ts, COALESCE(model, '?') AS model, "
            "         duration_ms AS ms, input_tokens + output_tokens AS tokens, "
            "         cost_usd AS cost, success AS ok "
            "  FROM run_metrics WHERE label = 'chat' ORDER BY id DESC LIMIT 20"
            ")"
            "SELECT (SELECT row_to_json(t) FROM t), "
            "       COALESCE((SELECT json_agg(d) FROM d), '[]'), "
            "       COALESCE((SELECT json_agg(r) FROM r), '[]')"
        ).fetchone()
    totals, daily, recent = row
    return {"totals": totals, "daily": daily, "recent": recent}


@contextmanager
def track(label):
    """Context manager that times a block and records it, even on error.

    Usage:
        with track("agent_run") as m:
            ... do work ...
            m["input_tokens"] = 30
            m["cost_usd"] = 0.0001
    """
    start = time.perf_counter()
    m = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    success = True
    error = None
    try:
        yield m
    except Exception as e:
        success = False
        error = str(e)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        record_run(
            label, duration_ms,
            m["input_tokens"], m["output_tokens"], m["cost_usd"],
            success, error,
        )