"""Local calendar store CRUD (Upgrade 002) — pure SQLite, no network."""
import pytest

from app.calendar import store


@pytest.fixture
def cal(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "cal.sqlite")
    store.init_calendar_table()
    return store


def test_add_and_list_roundtrip(cal):
    eid = cal.add_event("Dentist", "2026-07-10T15:00", "2026-07-10T15:30", "Clinic", "checkup")
    assert isinstance(eid, int)
    events = cal.list_events(start="2026-01-01T00:00")
    assert len(events) == 1
    assert events[0]["title"] == "Dentist"
    assert events[0]["location"] == "Clinic"


def test_list_orders_by_start(cal):
    cal.add_event("Later", "2026-07-10T09:00")
    cal.add_event("Earlier", "2026-07-08T09:00")
    titles = [e["title"] for e in cal.list_events(start="2026-01-01T00:00")]
    assert titles == ["Earlier", "Later"]


def test_date_range_filter(cal):
    cal.add_event("In", "2026-07-08T10:00")
    cal.add_event("Out", "2026-07-20T10:00")
    got = [e["title"] for e in cal.list_events("2026-07-07T00:00", "2026-07-09T23:59")]
    assert got == ["In"]


def test_find_matches_title_and_notes(cal):
    cal.add_event("Standup", "2026-07-08T09:00", notes="daily sync")
    cal.add_event("Lunch", "2026-07-08T12:00")
    assert [e["title"] for e in cal.find_events("stand")] == ["Standup"]
    assert [e["title"] for e in cal.find_events("sync")] == ["Standup"]
    assert cal.find_events("nope") == []


def test_delete(cal):
    eid = cal.add_event("Temp", "2026-07-08T09:00")
    assert cal.delete_event(eid) is True
    assert cal.delete_event(eid) is False           # already gone
    assert cal.delete_event(9999) is False          # never existed
    assert cal.list_events(start="2026-01-01T00:00") == []


def test_bad_datetime_rejected(cal):
    with pytest.raises(ValueError):
        cal.add_event("Bad", "next friday")


def test_export_ics(cal):
    cal.add_event("Dentist", "2026-07-10T15:00", "2026-07-10T15:30", notes="bring, forms")
    ics = cal.export_ics()
    assert ics.startswith("BEGIN:VCALENDAR")
    assert "BEGIN:VEVENT" in ics and "SUMMARY:Dentist" in ics
    assert "DTSTART:20260710T150000" in ics
    assert "bring\\, forms" in ics  # comma escaped per RFC 5545
