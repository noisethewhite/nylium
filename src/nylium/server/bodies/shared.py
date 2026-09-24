"""Shared machinery of the bodies package (ADR-0017, ADR-0018): the
pydantic config, the FastAPI path-binding marker and the forward-ref
resolution each domain module runs on import."""
from __future__ import annotations

import typing
from types import ModuleType
from typing import TYPE_CHECKING

from fastapi import Depends, params

if TYPE_CHECKING:
    from collections.abc import Mapping


# FastAPI binds a dataclass dependency's __init__ parameters from the
# path/query by name — that is how GET/DELETE requests become typed.
PATH_PARAMS: params.Depends = Depends()  # pyright: ignore[reportAny]


def resolve_route_hints(module: ModuleType) -> None:
    """Evaluate forward references in the route signatures of ``module``.

    A handler annotates its own class by name, which is not yet bound
    while the class body executes; resolve those annotations to the real
    classes now, before FastAPI inspects the signatures (it uses the
    dependency annotation as the Depends() target class verbatim)."""
    members = typing.cast("Mapping[str, object]", vars(module))
    for value in members.values():
        if not isinstance(value, type) or value.__module__ != module.__name__:
            continue
        attrs = typing.cast("Mapping[str, object]", vars(value))
        for attr in attrs.values():
            fn = typing.cast("object", getattr(attr, "__func__", attr))
            name = typing.cast("object", getattr(fn, "__name__", ""))
            if not callable(fn) or not isinstance(name, str):
                continue
            if not name.startswith("route"):
                continue
            fn.__annotations__ = typing.get_type_hints(
                fn, vars(module), include_extras=True
            )
