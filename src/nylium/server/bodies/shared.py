"""Shared machinery of the bodies package (ADR-0017, ADR-0018): the
pydantic config, the FastAPI path-binding marker, route self-registration
and the forward-ref resolution each domain module runs on import."""
from __future__ import annotations

import typing
from dataclasses import dataclass as plain_dataclass
from dataclasses import replace
from types import ModuleType
from typing import TYPE_CHECKING

from fastapi import Depends, params, status

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping


# FastAPI binds a dataclass dependency's __init__ parameters from the
# path/query by name — that is how GET/DELETE requests become typed.
PATH_PARAMS: params.Depends = Depends()  # pyright: ignore[reportAny]

CREATED: int = status.HTTP_201_CREATED
NO_CONTENT: int = status.HTTP_204_NO_CONTENT


@plain_dataclass(frozen=True)
class RouteSpec:
    """Wire metadata of one bodies route: where and how NyliumApp mounts
    it. ``handler`` is filled in by collect_route_specs."""

    path: str
    method: str
    status_code: int | None = None
    guarded: bool = True
    handler: Callable[..., object] | None = None


def api_route(
    path: str, method: str, *, status_code: int | None = None, guarded: bool = True
) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Stamp a route classmethod with its mount metadata, so NyliumApp can
    mount every bodies route from the declarations instead of a central
    add_api_route list. Sits UNDER @classmethod (sees the raw function).

    ``guarded=False`` marks the session-only / unauthenticated routes
    (auth ceremonies, token management) that skip the bearer guard —
    they carry their own auth dependency in the signature."""

    def decorator(fn: Callable[..., object]) -> Callable[..., object]:
        setattr(fn, "__route_spec__", RouteSpec(path, method, status_code, guarded))
        return fn

    return decorator


def collect_route_specs(*owners: object) -> list[RouteSpec]:
    """Gather every api_route-stamped classmethod, with the handler bound
    to its owning class. Owners: a package (scans its __all__) or a
    namespace class directly (auth_routes, token_routes)."""
    specs: list[RouteSpec] = []
    for owner in owners:
        if isinstance(owner, ModuleType):
            candidates: list[object] = [
                typing.cast("object", getattr(owner, export))
                for export in typing.cast("list[str]", owner.__all__)
            ]
        else:
            candidates = [owner]
        for candidate in candidates:
            if not isinstance(candidate, type):
                continue
            attrs = typing.cast("Mapping[str, object]", vars(candidate))
            for attr_name, member in attrs.items():
                fn = getattr(member, "__func__", member)
                spec = getattr(fn, "__route_spec__", None)
                if not isinstance(spec, RouteSpec):
                    continue
                handler = typing.cast(
                    "Callable[..., object]", getattr(candidate, attr_name)
                )
                specs.append(replace(spec, handler=handler))
    return specs


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
