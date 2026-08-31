"""Test bootstrap: every test runs against a freshly created schema in
a live Postgres. Set DATABASE_URL to a disposable database — the
fixture drops and recreates all tables around each test.
"""
import os

import pytest

from nylium.database.database import Database
from nylium.database.tables import Base


@pytest.fixture(autouse=True)
def _fresh_schema():
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set — tests need a live Postgres")
    engine = Database().engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
