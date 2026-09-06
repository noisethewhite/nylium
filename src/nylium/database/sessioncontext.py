from __future__ import annotations
from contextvars import Token
import sqlalchemy as sqla
from sqlalchemy.orm import Session
from typing import cast

from nylium.basic import LocalCtxVar
from nylium.system import Environment


_session = LocalCtxVar[Session | None]("session", None)
_engine: sqla.Engine | None = None


class SessionContext:
    _token: Token[Session | None] | None = None

    @staticmethod
    def get_session() -> Session:
        result = _session.get()
        if result is None:
            raise RuntimeError("Used SessionContext.get() outside of context.")
        return result

    @staticmethod
    def get_engine() -> sqla.Engine:
        global _engine
        if _engine is None:
            _engine = sqla.create_engine(Environment.database_url, pool_pre_ping=True, echo=False)
        return _engine

    def __enter__(self) -> None:
        if _session.get() is None:
            self._token = _session.set(Session(SessionContext.get_engine()))

    def __exit__(self, *_) -> None:
        if self._token is not None:
            cast(Session, _session.get()).close()
            _session.reset(self._token)
            self._token = None
