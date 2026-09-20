from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar
from functools import wraps

from nylium.database.sessioncontext import SessionContext


_P = ParamSpec("_P")
_R = TypeVar("_R")


def use_same_session(func: Callable[_P, _R]) -> Callable[_P, _R]:
    """Run ``func`` inside a SessionContext without committing.

    Joins the outermost session (or opens one that a nested
    ``commit_after_this`` will commit). Use for reads and for the inner
    steps of a multi-step write: the outermost call commits once,
    atomically.
    """

    @wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with SessionContext():
            return func(*args, **kwargs)

    return wrapper


def commit_after_this(func: Callable[_P, _R]) -> Callable[_P, _R]:
    """Run ``func`` inside a SessionContext and commit when it owns the session.

    The outermost call commits once, atomically; nested calls share the
    owner's session and leave the commit to it, so a failure mid-operation
    rolls back instead of leaving a half-written object.
    """

    @wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with SessionContext() as ctx:
            value = func(*args, **kwargs)
            if ctx.owns_session:
                SessionContext.get_session().commit()
            return value

    return wrapper
