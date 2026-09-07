from __future__ import annotations
from typing import TypeVar, Generic, TypeAlias, cast, overload
from collections.abc import Callable, Generator

import threading


_T = TypeVar("_T")
_R = TypeVar("_R")

_FGET_T: TypeAlias = Callable[[_T], _R]
_FSET_T: TypeAlias = Callable[[_T, _R],  None]
_FDEL_T: TypeAlias = Callable[[_T], None]
_FFOREACH_T: TypeAlias = Callable[[type[_T], _R], Generator[_T, None, None]]


class tableproperty(Generic[_T, _R]):
    _fget: _FGET_T[_T, _R] | None = None
    _fset: _FSET_T[_T, _R] | None = None
    _fdel: _FDEL_T[_T] | None = None
    _fforeach: _FFOREACH_T[_T, _R] | None = None
    _owner: type[_T] = cast(type[_T], None)
    _lock: threading.Lock

    def __set_name__(self, owner: type[_T], _: str) -> None:
        self._owner = owner

    def __init__(
        self,
        fget: _FGET_T[_T, _R] | None = None,
        fset: _FSET_T[_T, _R] | None = None,
        fdel: _FDEL_T[_T] | None = None,
        fforeach: _FFOREACH_T[_T, _R] | None = None,
        doc: str | None = None
    ) -> None:
        self._fget = fget
        self._fset = fset
        self._fdel = fdel
        self._fforeach = fforeach
        self._lock = threading.Lock()
        self.__doc__ = doc if doc is not None else (fget.__doc__ if fget else None)

    @overload
    def __get__(self, obj: _T, _: type[_T] | None = None) -> _R: ...

    @overload
    def __get__(self, obj: None, _: type[_T] | None = None) -> None: ...

    def __get__(self, obj: _T | None, _: type[_T] | None = None) -> _R | None:
        if self._fget is None:
            raise AttributeError("cannot get attribute.")
        if obj is not None:
            with self._lock:
                return self._fget(obj)

    def __set__(self, obj: _T | None, value: _R) -> None:
        if self._fset is None:
            raise AttributeError("cannot set attribute.")
        if obj is not None:
            self._fset(obj, value)

    def __del__(self, obj: _T | None) -> None:
        if self._fdel is None:
            raise AttributeError("cannot delete attribute.")
        if obj is not None:
            self._fdel(obj)

    def foreach(self, value: _R) -> Generator[_T, None, None]:
        if self._fforeach is None:
            raise AttributeError("cannot foreach attribute.")
        for obj in self._fforeach(self._owner, value):
            yield obj

    def getter(self, fget: _FGET_T[_T, _R]) -> tableproperty[_T, _R]:
        self._fget = fget
        return self

    def setter(self, fset: _FSET_T[_T, _R]) -> tableproperty[_T, _R]:
        self._fset = fset
        return self

    def deleter(self, fdel: _FDEL_T[_T]) -> tableproperty[_T, _R]:
        self._fdel = fdel
        return self

    def foreacher(self, fforeach: _FFOREACH_T[_T, _R]) -> tableproperty[_T, _R]:
        self._fforeach = fforeach
        return self
