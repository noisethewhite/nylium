"""Mount metadata of one API route (ADR-0017)."""
from __future__ import annotations

from dataclasses import dataclass as plain_dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@plain_dataclass(frozen=True)
class RouteSpec:
    """Where and how NyliumApp mounts a route. Route handlers self-declare
    path/method/status via ``NyliumApp.api_route``; ``handler`` is filled
    in when NyliumApp collects the stamped classmethods."""

    path: str
    method: str
    status_code: int | None = None
    guarded: bool = True
    handler: Callable[..., object] | None = None
