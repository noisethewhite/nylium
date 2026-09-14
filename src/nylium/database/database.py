from __future__ import annotations

from typing import cast

import sqlalchemy as sqla
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from nylium.database.sessioncontext import SessionContext


class _DatabaseMeta(type):
    @property
    def session(cls) -> Session:
        return SessionContext.get_session()

    @property
    def engine(cls) -> Engine:
        return SessionContext.get_engine()


class Database(metaclass=_DatabaseMeta):
    pass


def database_size_bytes() -> int:
    """Server-level footprint of the nylium database (ADR-0015 storage stats).

    An engine query, not a session/table read — lives beside ``Database`` so
    the api layer never reaches for SQLAlchemy directly.
    """
    with Database.engine.connect() as connection:
        return cast(
            int,
            connection.execute(
                sqla.select(sqla.func.pg_database_size(sqla.func.current_database()))
            ).scalar_one(),
        )
