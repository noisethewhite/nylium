from __future__ import annotations
from typing import TypeVar, ParamSpec, Concatenate
from functools import wraps
from collections.abc import Callable


_T = TypeVar("_T")
_R = TypeVar("_R")
_P = ParamSpec("_P")


def smartoverride(orig: Callable[Concatenate[_T, _P], _R]) -> Callable[[Callable[[_T], None]], Callable[Concatenate[_T, _P], _R]]:
    def decorator(func: Callable[[_T], None]) -> Callable[Concatenate[_T, _P], _R]:
        @wraps(orig)
        def wrapper(cls: _T, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            func(cls)
            return orig(cls, *args, **kwargs)
        return wrapper
    return decorator
