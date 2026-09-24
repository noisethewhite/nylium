from __future__ import annotations
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict


_VIEW_CONFIG = ConfigDict(strict=True)


@dataclass(config=_VIEW_CONFIG)
class StorageStats:
    """Disk usage of the blob-store volume plus nylium's own footprint."""

    total_bytes: int
    used_bytes: int
    free_bytes: int
    nylium_bytes: int
