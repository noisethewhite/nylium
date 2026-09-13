from __future__ import annotations
from typing import Self
from enum import StrEnum, EnumMeta
import os
import dotenv

from nylium.basic.namedstring import NamedString

class EnvEnum_Meta(EnumMeta):
    _dotenv_loaded: bool = False

    def load_dotenv(cls) -> None:
        if not cls._dotenv_loaded:
            _ = dotenv.load_dotenv()
            cls._dotenv_loaded = True


class EnvEnum(StrEnum, metaclass=EnvEnum_Meta):
    def _default(self) -> str:
        """Fallback for optional variables; required ones keep it empty."""
        return ""

    def __get__(self, instance: Self | None, owner: type[Self]) -> NamedString:
        type(self).load_dotenv()
        value = NamedString(self.value, os.environ.get(self) or self._default())
        if not value:
            missing = [
                name.name for name in owner
                if not os.environ.get(name.value) and not name._default()
            ]
            raise RuntimeError(f"Some environment variables are missing: {' ,'.join(missing)}.")
        return value
