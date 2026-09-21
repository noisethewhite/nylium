"""HTTP surface for nylium: FastAPI over the Api facade."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nylium.server.app import NyliumApp

__all__ = ["NyliumApp"]


def __getattr__(name: str) -> object:
    if name == "NyliumApp":
        # Deliberately lazy (PEP 562): keeps `nylium.server.errors` importable
        # without pulling the FastAPI app — this is what lets api/* import
        # ValidationError at module top without a cycle.
        from nylium.server.app import NyliumApp  # noqa: PLC0415

        return NyliumApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
