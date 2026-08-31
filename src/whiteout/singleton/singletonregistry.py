from __future__ import annotations
from typing import ClassVar, cast
from .singletonvars import SingletonVars


class _singletonreg_mcls(type):
    _data: ClassVar[dict[type, SingletonVars]]

    @property
    def data(cls) -> dict[type, SingletonVars]:
        mcls = type(cls)
        if not hasattr(mcls, "_data"):
            setattr(mcls, "_data", {})
        return cast(dict[type, SingletonVars], getattr(mcls, "_data"))

    def is_singleton(cls, t: type) -> bool:
        return cls.data.get(t) is not None


class SingletonRegistry(object, metaclass=_singletonreg_mcls):
    pass
