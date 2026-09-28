"""NyRef — the single base for every typed-uuid reference.

A reference *holds* its uuid (composition) instead of *being* one
(subclassing): a reference is not a string, never binds into a SQL
statement by accident, and two references of different domains never
compare equal even when the uuids match. Subclasses carry the table
lookup (``get()``) and their domain navigation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Self, override
from uuid import UUID

from pydantic_core import core_schema

if TYPE_CHECKING:
    from nylium.database.Table import Row


class NyRef(ABC):
    """A typed reference to one domain row: raw uuid inside, row outside."""

    __slots__: ClassVar[tuple[str, ...]] = ("_uuid",)

    _uuid: UUID

    def __init__(self, value: UUID | str | NyRef) -> None:
        if isinstance(value, NyRef):
            value = value._uuid
        self._uuid = value if isinstance(value, UUID) else UUID(value)

    @classmethod
    def of(cls, value: UUID | str | NyRef) -> Self:
        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        def _coerce(value: object) -> object:
            if isinstance(value, NyRef):
                return value
            if isinstance(value, UUID):
                return cls(value)
            return value

        def _serialize(ref: NyRef) -> UUID:
            return ref.uuid

        return core_schema.no_info_before_validator_function(
            _coerce,
            core_schema.is_instance_schema(
                cls,
                serialization=core_schema.plain_serializer_function_ser_schema(
                    _serialize,
                    return_schema=core_schema.uuid_schema(),
                ),
            ),
        )

    @property
    def uuid(self) -> UUID:
        return self._uuid

    @abstractmethod
    def get(self) -> "Row | None":
        """The row this reference points at, or ``None`` if it is gone."""

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, NyRef):
            return type(self) is type(other) and self._uuid == other._uuid
        return NotImplemented

    @override
    def __hash__(self) -> int:
        return hash((type(self), self._uuid))

    @override
    def __str__(self) -> str:
        return str(self._uuid)

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._uuid})"
