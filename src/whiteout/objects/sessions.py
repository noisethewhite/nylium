"""Session factory namespace. Owns the one place that knows how a
whiteout objects session is built."""
from __future__ import annotations

from sqlalchemy.orm import Session

from whiteout.database.database import Database


class sessions:
    @classmethod
    def new(cls) -> Session:
        return Session(Database().engine)
