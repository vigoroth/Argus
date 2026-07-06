"""term.py auth gating (Upgrade 012): the shell endpoint's two locks."""
import pytest

from app.web.auth import make_session_token, valid_token
from app.web.term import term_enabled


def test_term_enabled_matrix(monkeypatch):
    for bind, want in (("127.0.0.1", True), ("localhost", True), ("::1", True),
                       ("0.0.0.0", False), ("192.168.1.10", False)):
        monkeypatch.setenv("ARGUS_BIND", bind)
        monkeypatch.delenv("ARGUS_TERM_ALLOW_REMOTE", raising=False)
        monkeypatch.delenv("NEXUS_TERM_ALLOW_REMOTE", raising=False)
        assert term_enabled() is want, bind
    # explicit opt-in unlocks a remote bind
    monkeypatch.setenv("ARGUS_BIND", "0.0.0.0")
    monkeypatch.setenv("ARGUS_TERM_ALLOW_REMOTE", "1")
    assert term_enabled() is True


def test_token_validation():
    assert valid_token(make_session_token()) is True   # real signed token
    assert valid_token(None) is False
    assert valid_token("") is False
    assert valid_token("garbage.token.value") is False
    # tampered signature
    good = make_session_token()
    assert valid_token(good[:-4] + "AAAA") is False


def test_ws_rejects_unauthenticated():
    """WS handshake without a session cookie closes 4403 — no PTY is spawned."""
    from starlette.testclient import TestClient

    from app.web.server import app
    client = TestClient(app)
    with pytest.raises(Exception) as exc:  # starlette raises WebSocketDisconnect
        with client.websocket_connect("/term") as ws:
            ws.receive_text()
    assert "4403" in str(exc.value) or getattr(exc.value, "code", None) == 4403


def test_ws_claude_rejects_unauthenticated():
    from starlette.testclient import TestClient

    from app.web.server import app
    client = TestClient(app)
    with pytest.raises(Exception) as exc:
        with client.websocket_connect("/claude") as ws:
            ws.receive_text()
    assert "4403" in str(exc.value) or getattr(exc.value, "code", None) == 4403
