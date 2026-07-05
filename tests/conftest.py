"""Shared test fixtures and import-time env setup.

`app.web.auth` reads its credentials from the environment at import time, so
those vars must exist before any test imports it. We seed deterministic values
here (a known password + hash) so auth tests can exercise real bcrypt checks.
"""
import os

import bcrypt
import pytest

# Known credentials used by tests/test_auth.py. The password is "testpass".
TEST_USERNAME = "tester"
TEST_PASSWORD = "testpass"
TEST_PASSWORD_HASH = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
TEST_SESSION_SECRET = "unit-test-session-secret"

# Force-set (not setdefault): auth.py reads these at import, and tests must match
# these exact values regardless of any credentials in the developer's shell.
for prefix in ("NEXUS", "ARGUS"):
    os.environ[f"{prefix}_USERNAME"] = TEST_USERNAME
    os.environ[f"{prefix}_PASSWORD_HASH"] = TEST_PASSWORD_HASH
    os.environ[f"{prefix}_SESSION_SECRET"] = TEST_SESSION_SECRET


@pytest.fixture
def test_username() -> str:
    return TEST_USERNAME


@pytest.fixture
def test_password() -> str:
    return TEST_PASSWORD
