"""HTTP surface for nylium: FastAPI over the Api facade."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nylium.server.app import NyliumApp

__all__ = ["NyliumApp"]


def __getattr__(name: str) -> object:
    if name == "NyliumApp":
        from nylium.server.app import NyliumApp

        return NyliumApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
