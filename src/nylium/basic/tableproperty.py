"""A property that can also answer "which objects have this value".

Mirrors the builtin ``property`` (fget/fset/fdel, decorator builders) and
adds a fourth accessor, ``fforeach``: given a value, it lazily yields every
owner instance whose field equals it. Class access returns the descriptor
itself, so ``Xxx.field.foreach(value)`` runs the reverse lookup without an
instance — the table-backed subclass in ``nylium.database.tabledomain``
turns that into a column scan.
"""
from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Generic, TypeAlias, TypeVar, cast, overload

_T = TypeVar("_T")
_R = TypeVar("_R")

_FGET_T: TypeAlias = Callable[[_T], _R]
_FSET_T: TypeAlias = Callable[[_T, _R], None]
_FDEL_T: TypeAlias = Callable[[_T], None]
_FFOREACH_T: TypeAlias = Callable[[type[_T], _R], Generator[_T, None, None]]


class tableproperty(Generic[_T, _R]):
    """A ``property`` with a reverse lookup.

    ``_owner`` is bound by ``__set_name__`` at class-creation; the
    class-level default only satisfies the strict-initializer lint and is
    never observed.
    """

    _fget: _FGET_T[_T, _R] | None = None
    _fset: _FSET_T[_T, _R] | None = None
    _fdel: _FDEL_T[_T] | None = None
    _fforeach: _FFOREACH_T[_T, _R] | None = None
    _owner: type[_T] = cast(type[_T], None)

    def __init__(
        self,
        fget: _FGET_T[_T, _R] | None = None,
        fset: _FSET_T[_T, _R] | None = None,
        fdel: _FDEL_T[_T] | None = None,
        fforeach: _FFOREACH_T[_T, _R] | None = None,
        doc: str | None = None,
    ) -> None:
        self._fget = fget
        self._fset = fset
        self._fdel = fdel
        self._fforeach = fforeach
        self.__doc__ = doc if doc is not None else (fget.__doc__ if fget else None)

    def __set_name__(self, owner: type[_T], _: str) -> None:
        self._owner = owner

    @overload
    def __get__(self, obj: None, _: type[_T] | None = None) -> tableproperty[_T, _R]: ...

    @overload
    def __get__(self, obj: _T, _: type[_T] | None = None) -> _R: ...

    def __get__(
        self, obj: _T | None, _: type[_T] | None = None
    ) -> tableproperty[_T, _R] | _R:
        if obj is None:
            return self
        if self._fget is None:
            raise AttributeError("unreadable attribute")
        return self._fget(obj)

    def __set__(self, obj: _T, value: _R) -> None:
        if self._fset is None:
            raise AttributeError("can't set attribute")
        self._fset(obj, value)

    def __delete__(self, obj: _T) -> None:
        if self._fdel is None:
            raise AttributeError("can't delete attribute")
        self._fdel(obj)

    def foreach(self, value: _R) -> Generator[_T, None, None]:
        """Every owner instance whose field equals ``value``, lazily."""
        if self._fforeach is None:
            raise AttributeError("no reverse lookup on this attribute")
        yield from self._fforeach(self._owner, value)

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
