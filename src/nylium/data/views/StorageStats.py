from __future__ import annotations
from pydantic.dataclasses import dataclass
from nylium.Constants import Constants




@dataclass(config=Constants.Pydantic.VIEW_CONFIG)
class StorageStats:
    """Disk usage of the blob-store volume plus nylium's own footprint."""

    total_bytes: int
    used_bytes: int
    free_bytes: int
    nylium_bytes: int
