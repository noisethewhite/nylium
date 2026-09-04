"""Test bootstrap: every test runs against a freshly created schema in
a live Postgres. Set DATABASE_URL to a disposable database — the
fixture drops and recreates all tables around each test.
"""
import secrets

import pytest
from fastapi.testclient import TestClient

from nylium.system import Environment
from nylium.database.database import Database
from nylium.database.tables import AuthCredentials, AuthUsers, Base
from nylium.auth.sessions import sessions
from nylium.server import NyliumApp


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """RP config for WebAuthn options — read lazily from the environment."""
    monkeypatch.setenv("RP_ID", "localhost")
    monkeypatch.setenv("RP_ORIGIN", "http://testserver")
    # ADR-0006: blobs land in a per-test tmp dir
    monkeypatch.setenv("FILES_DIR", str(tmp_path / "files"))


@pytest.fixture(autouse=True)
def _fresh_schema():
    try:
        _ = Environment.database_url
    except RuntimeError:
        pytest.skip("DATABASE_URL not set — tests need a live Postgres")
    engine = Database.engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def auth_client() -> TestClient:
    """Client with a live session cookie: owner user + one credential +
    issued token, planted directly (passkey bytes can't be faked here)."""
    user = AuthUsers.create("owner")
    AuthCredentials.register(user.uuid, secrets.token_bytes(32), b"pk", 0, "")
    client = TestClient(NyliumApp.create())
    client.cookies.set(sessions.COOKIE_NAME, sessions.issue(user.uuid))
    return client
