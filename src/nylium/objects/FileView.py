from __future__ import annotations
from nylium.data.rows import File
from typing import Self
from uuid import UUID
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict


_VIEW_CONFIG = ConfigDict(strict=True)


@dataclass(config=_VIEW_CONFIG)
class FileView:
    """One stored file's metadata (contracts.ts FileView) — the wire
    projection, kept next to the domain facade it renders."""

    uuid: UUID
    type_name: str
    name: str
    mime: str
    size_bytes: int

    @classmethod
    def from_row(cls, file: File) -> Self:
        return cls(
            uuid=file.uuid,
            type_name=file.type_name,
            name=file.name,
            mime=file.mime,
            size_bytes=file.size_bytes,
        )
