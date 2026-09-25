from __future__ import annotations
from typing import Protocol
from uuid import UUID

from nylium.uuid import ObjectUUID


class NyObjectProtocol(Protocol):
    """The slice of NyObject that lower layers are allowed to rely on."""

    _uuid: ObjectUUID

    @classmethod
    def wrap(cls, uuid: UUID) -> "NyObjectProtocol": ...

    @property
    def uuid(self) -> ObjectUUID: ...

    def delete(self) -> None: ...
