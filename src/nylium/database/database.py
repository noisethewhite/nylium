from __future__ import annotations

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
