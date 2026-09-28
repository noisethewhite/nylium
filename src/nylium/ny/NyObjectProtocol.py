from __future__ import annotations
from typing import Protocol
from uuid import UUID

from nylium.uuid import ObjectRef


class NyObjectProtocol(Protocol):
    """The slice of NyObject that lower layers are allowed to rely on."""

    _uuid: ObjectRef

    @classmethod
    def wrap(cls, uuid: UUID) -> "NyObjectProtocol": ...

    @property
    def uuid(self) -> ObjectRef: ...

    def delete(self) -> None: ...
