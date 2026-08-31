"""Test bootstrap: every test runs against a freshly created schema in
a live Postgres. Set DATABASE_URL to a disposable database — the
fixture drops and recreates all tables around each test.
"""
import pytest

from nylium.system import Environment
from nylium.database.database import Database
from nylium.database.tables import Base


@pytest.fixture(autouse=True)
def _fresh_schema():
    try:
        _ = Environment.database_url
    except RuntimeError:
        pytest.skip("DATABASE_URL not set — tests need a live Postgres")
    engine = Database().engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
