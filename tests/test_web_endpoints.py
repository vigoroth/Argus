"""Web endpoint coverage (Upgrade 012): auth wall, login flow, CRUD smoke.

Uses TestClient against the real app; Postgres init is skipped via
ARGUS_SKIP_DB_INIT (conftest), and stores are pointed at temp files.
"""
import pytest
from starlette.testclient import TestClient

# must match the deterministic credentials seeded in tests/conftest.py
TEST_USERNAME, TEST_PASSWORD = "tester", "testpass"


@pytest.fixture(scope="module")
def app():
    from app.web.server import app
    return app


@pytest.fixture()
def anon(app):
    return TestClient(app)


@pytest.fixture()
def authed(app):
    c = TestClient(app)
    r = c.post("/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
               follow_redirects=False)
    assert r.status_code == 303 and "argus_session" in c.cookies
    return c


# ── auth wall ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/skills", "/models", "/calendar", "/uploads",
                                  "/stats", "/status", "/secrets"])
def test_api_requires_auth(anon, path):
    assert anon.get(path).status_code == 401


def test_root_redirects_to_login(anon):
    r = anon.get("/", follow_redirects=False)
    assert r.status_code == 303 and "/login" in r.headers["location"]


def test_bad_login_no_cookie(anon):
    r = anon.post("/login", data={"username": TEST_USERNAME, "password": "wrong"},
                  follow_redirects=False)
    assert "argus_session" not in anon.cookies
    assert r.status_code in (200, 303, 401)


# ── authed smoke ─────────────────────────────────────────────────────────────

def test_calendar_crud_roundtrip(authed, tmp_path, monkeypatch):
    from app.calendar import store
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "cal.sqlite")
    store.init_calendar_table()

    r = authed.post("/calendar", json={"title": "Test evt", "start": "2030-01-01T10:00"})
    assert r.status_code == 200
    eid = r.json()["id"]
    titles = [e["title"] for e in authed.get("/calendar").json()]
    assert "Test evt" in titles
    assert authed.post("/calendar", json={"title": "bad", "start": "not-a-date"}).status_code == 400
    assert authed.delete(f"/calendar/{eid}").json()["ok"] is True


def test_skills_payload_shape(authed):
    d = authed.get("/skills").json()
    assert set(d) >= {"live", "pending", "agents", "pending_tools"}
    assert any(s["name"] == "lab-upgrade" for s in d["live"])          # seed skill
    assert any(a["name"] == "data-analyst" for a in d["agents"])       # built-in agent


def test_skills_approve_slug_guard(authed):
    assert authed.post("/skills/..%2Fevil/approve").status_code == 404
    assert authed.post("/tools/..%2Fevil/approve").status_code == 404


def test_upload_validation(authed, tmp_path, monkeypatch):
    from app.web import uploads
    monkeypatch.setattr(uploads, "UPLOADS_DIR", tmp_path / "up")
    # bad extension -> 400
    r = authed.post("/upload", files={"file": ("evil.py", b"print(1)")})
    assert r.status_code == 400
    # good file round-trips and is listed
    r = authed.post("/upload", files={"file": ("t.csv", b"a,b\n1,2\n")})
    assert r.status_code == 200 and r.json()["name"] == "t.csv"
    assert [f["name"] for f in authed.get("/uploads").json()] == ["t.csv"]


def test_upload_size_cap(authed, tmp_path, monkeypatch):
    from app.web import uploads
    monkeypatch.setattr(uploads, "UPLOADS_DIR", tmp_path / "up")
    monkeypatch.setattr(uploads, "MAX_UPLOAD_BYTES", 10)
    r = authed.post("/upload", files={"file": ("big.csv", b"x" * 100)})
    assert r.status_code == 413


def test_models_pull_rejects_bad_name(authed):
    r = authed.post("/models/pull", json={"name": "a;rm -rf /"})
    assert r.status_code == 400
