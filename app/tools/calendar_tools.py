"""Calendar tools — let the agent manage the local SQLite calendar (Upgrade 002).

Datetimes are ISO 8601 (e.g. 2026-07-10T15:00). The agent resolves relative phrases
("friday 3pm") to ISO using the current date/time injected into its context.
"""
from langchain_core.tools import tool

from app.calendar import store


def _fmt(e: dict) -> str:
    when = e["start_ts"] + (f" → {e['end_ts']}" if e.get("end_ts") else "")
    extra = f" @ {e['location']}" if e.get("location") else ""
    note = f" — {e['notes']}" if e.get("notes") else ""
    return f"#{e['id']} {e['title']} ({when}){extra}{note}"


@tool
def add_event(title: str, start: str, end: str = "", location: str = "",
              notes: str = "") -> str:
    """Add an event to the user's calendar.
    `start` (and optional `end`) must be ISO 8601 datetimes, e.g. 2026-07-10T15:00.
    Returns the created event with its id.
    """
    try:
        eid = store.add_event(title, start, end or None, location or None, notes or None)
    except ValueError:
        return "ERROR: start/end must be ISO 8601, e.g. 2026-07-10T15:00."
    except Exception as e:
        return f"ERROR: {e}"
    return "Added event " + _fmt({"id": eid, "title": title, "start_ts": start,
                                  "end_ts": end or None, "location": location or None,
                                  "notes": notes or None})


@tool
def list_events(start: str = "", end: str = "") -> str:
    """List calendar events, optionally within an ISO 8601 date range [start, end].
    With no range, returns upcoming events (from now forward).
    """
    try:
        events = store.list_events(start or None, end or None)
    except ValueError:
        return "ERROR: start/end must be ISO 8601 dates."
    except Exception as e:
        return f"ERROR: {e}"
    if not events:
        return "No events found."
    return "\n".join(_fmt(e) for e in events)


@tool
def find_events(query: str) -> str:
    """Find calendar events whose title or notes contain the query text."""
    try:
        events = store.find_events(query)
    except Exception as e:
        return f"ERROR: {e}"
    if not events:
        return f"No events matching '{query}'."
    return "\n".join(_fmt(e) for e in events)


@tool
def delete_event(event_id: int) -> str:
    """Delete ONE calendar event by its numeric id. Destructive — first confirm with
    the user which event (use list_events/find_events to get the id), then delete.
    """
    try:
        ok = store.delete_event(int(event_id))
    except Exception as e:
        return f"ERROR: {e}"
    return f"Deleted event #{event_id}." if ok else f"No event #{event_id} to delete."


CALENDAR_TOOLS = [add_event, list_events, find_events, delete_event]
