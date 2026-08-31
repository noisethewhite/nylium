from __future__ import annotations
import threading


class SingletonVars(object):
    _instance: object | None
    _lock: threading.Lock
    _is_initialized: bool
    _type: type

    def __init__(self, t: type) -> None:
        self._instance = None
        self._lock = threading.Lock()
        self._is_initialized = False
        self._type = t

    @property
    def instance(self) -> object | None:
        return self._instance

    @instance.setter
    def instance(self, obj: object) -> None:
        if self._instance is None:
            self._instance = obj

    @property
    def lock(self) -> threading.Lock:
        return self._lock

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    @is_initialized.setter
    def is_initialized(self, value: bool) -> None:
        if value:
            self._is_initialized = True

    @property
    def t(self) -> type:
        return self._type
