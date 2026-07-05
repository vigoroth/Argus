"""Session token + login checks in app/web/auth.py.

Credentials come from the env vars seeded in conftest.py.
"""
from app.web import auth


def test_token_round_trip():
    token = auth.make_session_token()
    assert auth.valid_token(token) is True


def test_none_token_rejected():
    assert auth.valid_token(None) is False
    assert auth.valid_token("") is False


def test_tampered_token_rejected():
    token = auth.make_session_token()
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    assert auth.valid_token(tampered) is False


def test_check_login_success(test_username, test_password):
    assert auth.check_login(test_username, test_password) is True


def test_check_login_wrong_password(test_username):
    assert auth.check_login(test_username, "wrong") is False


def test_check_login_wrong_username(test_password):
    assert auth.check_login("intruder", test_password) is False
