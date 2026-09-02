from __future__ import annotations
from sqlalchemy import Engine
from sqlalchemy.orm import Session
import threading


_local = threading.local()


class LocalSession:
    _session: Session
    _owned: bool

    def __init__(self, engine: Engine) -> None:
        current = getattr(_local, "session", None)
        if current is None:
            self._session = Session(engine, expire_on_commit=False)
            self._owned = True
            _local.session = self._session
        else:
            self._session = current
            self._owned = False

    @property
    def value(self) -> Session:
        return self._session

    def close(self) -> None:
        if self._owned:
            try:
                self._session.close()
            finally:
                _local.session = None

    def commit(self) -> None:
        if self._owned:
            self._session.commit()
