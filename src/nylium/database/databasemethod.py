from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar
from functools import wraps

from nylium.database.sessioncontext import SessionContext


_P = ParamSpec("_P")
_R = TypeVar("_R")


def databasemethod(commit: bool) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    def decorator(func: Callable[_P, _R]) -> Callable[_P, _R]:
        @wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            with SessionContext():
                value = func(*args, **kwargs)
                if commit:
                    SessionContext.get_session().commit()
                return value
        return wrapper
    return decorator
