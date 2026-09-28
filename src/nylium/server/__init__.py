"""HTTP surface for nylium: FastAPI over the Api facade."""
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nylium.server.NyliumApp import NyliumApp
    from nylium.server.PropCodec import PropCodec
    from nylium.server.StaticSpa import StaticSpa
    from nylium.server.serve import serve

__all__ = ["NyliumApp", "PropCodec", "StaticSpa", "serve"]


def __getattr__(name: str) -> object:
    # Deliberately lazy (PEP 562): keeps `nylium.server.errors` importable
    # without pulling the FastAPI app — this is what lets api/* import
    # ValidationError at module top without a cycle.
    if name in {"NyliumApp", "PropCodec", "StaticSpa", "serve"}:
        if name == "NyliumApp":
            from nylium.server.NyliumApp import NyliumApp  # noqa: PLC0415

            value: object = NyliumApp
        elif name == "PropCodec":
            from nylium.server.PropCodec import PropCodec  # noqa: PLC0415

            value = PropCodec
        elif name == "StaticSpa":
            from nylium.server.StaticSpa import StaticSpa  # noqa: PLC0415

            value = StaticSpa
        else:
            from nylium.server.serve import serve  # noqa: PLC0415

            value = serve
        # Importing the submodule sets `server.<Name>` on this package to
        # the *module*; overwrite it with the actual object so
        # `from nylium.server import <Name>` keeps yielding the object.
        setattr(sys.modules[__name__], name, value)
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
