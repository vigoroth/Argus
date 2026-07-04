"""Simple single-password auth for protecting the Nexus instance.
Password is checked against a bcrypt hash in .env; a signed cookie holds the session.
"""
import os
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
import hmac

USERNAME = os.environ["NEXUS_USERNAME"]
PASSWORD_HASH = os.environ["NEXUS_PASSWORD_HASH"].encode()
SESSION_SECRET = os.environ["NEXUS_SESSION_SECRET"]
COOKIE_NAME = "nexus_session"
MAX_AGE = 60 * 60 * 24 * 7  # 7 days

_serializer = URLSafeTimedSerializer(SESSION_SECRET)


def check_login(username: str, password: str) -> bool:
    """Constant-time check of username + bcrypt password."""
    user_ok = hmac.compare_digest(username, USERNAME)
    try:
        pw_ok = bcrypt.checkpw(password.encode(), PASSWORD_HASH)
    except Exception:
        pw_ok = False
    return user_ok and pw_ok


def make_session_token() -> str:
    return _serializer.dumps({"authed": True})


def valid_token(token: str | None) -> bool:
    """Validate a raw session token (shared by HTTP requests and WS handshakes)."""
    if not token:
        return False
    try:
        _serializer.loads(token, max_age=MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def valid_session(request: Request) -> bool:
    return valid_token(request.cookies.get(COOKIE_NAME))


def require_auth(request: Request):
    """Dependency: allow the request only if a valid session cookie is present."""
    if not valid_session(request):
        raise HTTPException(status_code=401, detail="Not authenticated")