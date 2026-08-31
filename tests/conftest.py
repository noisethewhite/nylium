"""Test bootstrap: every test runs against a freshly created schema in
a live Postgres. Set DATABASE_URL to a disposable database — the
fixture drops and recreates all tables around each test.
"""
import os

import dotenv
import pytest

# Load .env up front: EnvEnum loads dotenv lazily on first attribute access,
# but the skip check below reads os.environ before any Environment access.
dotenv.load_dotenv()

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
