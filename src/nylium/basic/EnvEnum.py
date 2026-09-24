from __future__ import annotations
from typing import Self, ClassVar
from enum import StrEnum, EnumMeta
import os
import dotenv

from nylium.basic.NamedString import NamedString
from nylium.basic.smartoverride import smartoverride

class _EnvEnum_Meta(EnumMeta):
    _dotenv_loaded: ClassVar[bool] = False

    @smartoverride(EnumMeta.__new__)
    def __new__(mcls) -> None:
        if not mcls._dotenv_loaded:
            _ = dotenv.load_dotenv()
            mcls._dotenv_loaded = True


class EnvEnum(StrEnum, metaclass=_EnvEnum_Meta):
    def _default(self) -> str:
        """Fallback for optional variables; required ones keep it empty."""
        return ""

    def __get__(self, instance: Self | None, owner: type[Self]) -> NamedString:
        value = NamedString(self.value, os.environ.get(self) or self._default())
        if not value:
            missing = [
                name.name for name in owner
                if not os.environ.get(name.value) and not name._default()
            ]
            raise RuntimeError(f"Some environment variables are missing: {' ,'.join(missing)}.")
        return value
