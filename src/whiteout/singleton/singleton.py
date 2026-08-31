from __future__ import annotations
from typing import TypeVar, cast, ParamSpec, Protocol, Generic
import inspect

from .singletonvars import SingletonVars
from .singletonregistry import SingletonRegistry


_T = TypeVar(name="_T")
_Tc = TypeVar(name="_Tc", covariant=True)
_P = ParamSpec(name="_P")


class _WithNew(Protocol, Generic[_Tc, _P]):
    def __new__(cls, *args: _P.args, **kwargs: _P.kwargs) -> _Tc: ...


def singleton(_cls: type[_WithNew[_T, _P]]) -> type[_WithNew[_T, _P]]:
    if len(inspect.signature(_cls.__init__).parameters) != 1:
        raise TypeError(f"{_cls.__name__}.__init__ must only accept 1 argument: self.")

    if _cls not in SingletonRegistry.data:
        SingletonRegistry.data[_cls] = SingletonVars(_cls)
    else:
        raise TypeError("This class is already a singleton.")

    orig_new = _cls.__new__
    orig_init = _cls.__init__

    def __new__(cls: type[_WithNew[_T, _P]], *args: _P.args, **kwargs: _P.kwargs) -> _WithNew[_T, _P]:
        reg_data = SingletonRegistry.data[cls]
        if reg_data.instance is None:
            with reg_data.lock:
                if reg_data.instance is None:
                    reg_data.instance = orig_new(cls, *args, **kwargs)
        return cast(_WithNew[_T, _P], reg_data.instance)

    def __init__(self: object) -> None:
        reg_data = SingletonRegistry.data[type(self)]
        if not reg_data.is_initialized:
            orig_init(cast(_WithNew[_T, _P], self))
            reg_data.is_initialized = True


    setattr(_cls, "__new__", staticmethod(__new__))
    setattr(_cls, "__init__", __init__)

    return _cls
