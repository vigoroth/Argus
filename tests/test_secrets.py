"""API-key secret store: Fernet crypto + provider mapping.

secrets_store imports psycopg lazily (only inside _conn), so the crypto helpers
import and run without the DB driver. The DB-backed functions are covered by the
unknown-provider guard, which fires before any DB access.
"""
from app.web.secrets_store import PROVIDERS, _fernet, set_secret


def test_fernet_round_trip():
    token = _fernet().encrypt(b"sk-secret-value")
    assert _fernet().decrypt(token) == b"sk-secret-value"


def test_fernet_is_stable_across_calls():
    # derived deterministically from ARGUS_SESSION_SECRET (seeded in conftest),
    # so a token from one instance decrypts on another
    token = _fernet().encrypt(b"hello")
    assert _fernet().decrypt(token) == b"hello"


def test_provider_mapping():
    assert PROVIDERS["openai"] == ("OPENAI_API_KEY", "openai_api_key")
    assert PROVIDERS["anthropic"] == ("ANTHROPIC_API_KEY", "anthropic_api_key")
    assert PROVIDERS["google"] == ("GOOGLE_API_KEY", "google_api_key")


def test_set_secret_rejects_unknown_provider():
    # the guard raises before any DB access, so this needs no psycopg
    try:
        set_secret("mystery", "key")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
