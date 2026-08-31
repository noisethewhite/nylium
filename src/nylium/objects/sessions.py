"""Session factory namespace. Owns the one place that knows how a
nylium objects session is built."""
from __future__ import annotations

from sqlalchemy.orm import Session

from nylium.database.database import Database


class sessions:
    @classmethod
    def new(cls) -> Session:
        return Session(Database().engine)
