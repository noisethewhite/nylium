from __future__ import annotations
from typing import Annotated
from nylium.api.Api import Api
from nylium.server.bodies.shared import PATH_PARAMS
from nylium.data.views.StorageStats import StorageStats
from dataclasses import dataclass as plain_dataclass
import sys
from nylium.server.bodies.shared import resolve_route_hints


@plain_dataclass
class StorageRequest:
    """No-input request of GET /storage."""

    @classmethod
    def route(cls, _request: Annotated["StorageRequest", PATH_PARAMS]) -> StorageStats:
        stats = Api.storage_stats()
        return StorageStats(
            total_bytes=stats["total_bytes"],
            used_bytes=stats["used_bytes"],
            free_bytes=stats["free_bytes"],
            nylium_bytes=stats["nylium_bytes"],
        )


resolve_route_hints(sys.modules[__name__])
