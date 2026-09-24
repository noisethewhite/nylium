from __future__ import annotations
from typing import Protocol
from uuid import UUID


class NyObjectShape(Protocol):
    """The slice of NyObject that lower layers are allowed to rely on."""

    _uuid: UUID

    @classmethod
    def wrap(cls, uuid: UUID) -> "NyObjectShape": ...

    @property
    def uuid(self) -> UUID: ...

    def delete(self) -> None: ...
