"""Local calendar — a self-contained SQLite event store (Upgrade 002).

Local-first: no external calendar, no OAuth. Just a `data/calendar.sqlite` table the
agent manages through the calendar tools. Datetimes are ISO 8601 text — `datetime.
fromisoformat` validates them and ISO strings sort/compare lexically, so date-range
filtering is a plain string BETWEEN (no new dependency).
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.logging_config import get_logger

log = get_logger("argus.calendar")

DB_PATH = Path("data/calendar.sqlite")


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_calendar_table() -> None:
    """Create the events table if absent. Safe to call every boot."""
    with _conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_ts TEXT NOT NULL,     -- ISO 8601
                end_ts TEXT,                -- ISO 8601, nullable
                location TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )


def _iso(value: str) -> str:
    """Validate + normalize an ISO 8601 datetime string (raises ValueError if bad)."""
    return datetime.fromisoformat(value).isoformat()


def add_event(title: str, start: str, end: str | None = None,
              location: str | None = None, notes: str | None = None) -> int:
    """Insert an event; returns its id. `start`/`end` must be ISO 8601."""
    start = _iso(start)
    end = _iso(end) if end else None
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO events (title, start_ts, end_ts, location, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, start, end, location, notes),
        )
        return cur.lastrowid


def list_events(start: str | None = None, end: str | None = None) -> list[dict]:
    """Events overlapping [start, end], ordered by start. Both bounds optional;
    with neither, returns everything from now forward (upcoming)."""
    if start is None and end is None:
        start = datetime.now().isoformat()
    clauses, params = [], []
    if start is not None:
        clauses.append("(end_ts IS NULL AND start_ts >= ?) OR end_ts >= ?")
        params += [_iso(start), _iso(start)]
    if end is not None:
        clauses.append("start_ts <= ?")
        params.append(_iso(end))
    where = (" WHERE " + " AND ".join(f"({c})" for c in clauses)) if clauses else ""
    with _conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM events{where} ORDER BY start_ts", params).fetchall()
    return [dict(r) for r in rows]


def find_events(query: str) -> list[dict]:
    """Events whose title or notes contain `query` (case-insensitive), by start."""
    like = f"%{query}%"
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE title LIKE ? COLLATE NOCASE "
            "OR notes LIKE ? COLLATE NOCASE ORDER BY start_ts", (like, like)).fetchall()
    return [dict(r) for r in rows]


def delete_event(event_id: int) -> bool:
    """Delete one event by id. Returns True if a row was removed."""
    with _conn() as conn:
        cur = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        return cur.rowcount > 0


def _ics_dt(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%Y%m%dT%H%M%S")


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def export_ics() -> str:
    """Serialize all events to an iCalendar (RFC 5545) string, so the user can
    subscribe from any calendar app. Hand-rolled — no dependency."""
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Argus//Calendar//EN"]
    for e in list_events(start="0001-01-01T00:00"):  # all events, chronological
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{e['id']}@argus")
        lines.append("DTSTART:" + _ics_dt(e["start_ts"]))
        if e.get("end_ts"):
            lines.append("DTEND:" + _ics_dt(e["end_ts"]))
        lines.append("SUMMARY:" + _ics_escape(e["title"]))
        if e.get("location"):
            lines.append("LOCATION:" + _ics_escape(e["location"]))
        if e.get("notes"):
            lines.append("DESCRIPTION:" + _ics_escape(e["notes"]))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
