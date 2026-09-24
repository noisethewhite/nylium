"""HTTP surface for nylium: FastAPI over the Api facade."""
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nylium.server.NyliumApp import NyliumApp

__all__ = ["NyliumApp"]


def __getattr__(name: str) -> object:
    if name == "NyliumApp":
        # Deliberately lazy (PEP 562): keeps `nylium.server.errors` importable
        # without pulling the FastAPI app — this is what lets api/* import
        # ValidationError at module top without a cycle.
        from nylium.server.NyliumApp import NyliumApp  # noqa: PLC0415

        # Importing the submodule sets `server.NyliumApp` on this package to
        # the *module*; overwrite it with the class so
        # `from nylium.server import NyliumApp` keeps yielding the class.
        setattr(sys.modules[__name__], "NyliumApp", NyliumApp)
        return NyliumApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
