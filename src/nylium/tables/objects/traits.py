# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
from __future__ import annotations

from collections.abc import Generator
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from nylium.database import Database, databasemethod
from nylium.database.table import Row, Table
from nylium.tables.base import reg
from nylium.tables.objects.props import Prop, props

__all__ = [
    "TABLE_Traits",
    "TABLE_TypeTraits",
    "Trait",
    "Traits",
    "TypeTrait",
    "TypeTraits",
    "traits",
    "type_traits",
]

# ADR-0013: a trait is a named, colored bundle of prop definitions.
# Attaching a trait to a type gives the type those props (the *effective*
# schema, see Type.props); the trait owns the prop rows, values stay
# keyed by (inst, prop) and don't care who owns the prop.


@reg.mapped_as_dataclass
class TABLE_Traits:
    __tablename__: ClassVar[str] = "traits"

    uuid: Mapped[UUID] = mapped_column(
        primary_key=True, default_factory=uuid4, kw_only=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    color: Mapped[str] = mapped_column(Text, nullable=False)


@reg.mapped_as_dataclass
class TABLE_TypeTraits:
    """Which trait is attached to which type, in attach order."""

    __tablename__: ClassVar[str] = "type_traits"

    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), primary_key=True
    )
    trait_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("traits.uuid", ondelete="CASCADE"), primary_key=True
    )
    # trait prop groups render after the type's own props, in this order
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class Trait(Row):
    """One trait: a writable snapshot of a TABLE_Traits row."""

    __table__: ClassVar[type[object]] = TABLE_Traits

    uuid: UUID
    name: str
    color: str

    @property
    def props(self) -> Generator[Prop, None, None]:
        """This trait's props, in display order."""
        yield from sorted(
            props.where(owner_trait_uuid=self.uuid), key=lambda p: p.position
        )

    def wire(self) -> dict[str, object]:
        """The JSON-safe wire shape, matching web/src/contracts.ts TraitView."""
        return {
            "name": self.name,
            "color": self.color,
            "props": [prop.wire() for prop in self.props],
            "attached": list(self.attached),
        }

    @property
    def attached(self) -> Generator[str, None, None]:
        """Names of types this trait is attached to, in attach order."""
        from nylium.tables.objects.types import types

        links = sorted(
            type_traits.where(trait_uuid=self.uuid), key=lambda link: link.position
        )
        for link in links:
            owner = types.get(link.type_uuid)
            if owner is not None:
                yield owner.name


class Traits(Table[UUID, Trait]):
    """The traits table as a Mapping of writable traits."""

    __row__: ClassVar[type[Row]] = Trait

    @databasemethod(commit=True)
    def create(self, name: str, color: str) -> Trait:
        row = TABLE_Traits(name=name, color=color)
        Database.session.add(row)
        Database.session.flush()
        return Trait(row)

    @databasemethod(commit=True)
    def delete(self, uuid: UUID) -> None:
        row = Database.session.get(TABLE_Traits, uuid)
        if row is not None:
            Database.session.delete(row)  # its props cascade


traits = Traits()


class TypeTrait(Row):
    """One attach edge: a writable snapshot of a TABLE_TypeTraits row."""

    __table__: ClassVar[type[object]] = TABLE_TypeTraits

    type_uuid: UUID
    trait_uuid: UUID
    position: int


class TypeTraits(Table[tuple[UUID, UUID], TypeTrait]):
    """The attach edges as a Mapping keyed by (type_uuid, trait_uuid)."""

    __row__: ClassVar[type[Row]] = TypeTrait

    @databasemethod(commit=True)
    def attach(self, type_uuid: UUID, trait_uuid: UUID, position: int) -> TypeTrait:
        row = TABLE_TypeTraits(
            type_uuid=type_uuid, trait_uuid=trait_uuid, position=position
        )
        Database.session.add(row)
        Database.session.flush()
        return TypeTrait(row)

    @databasemethod(commit=True)
    def detach(self, type_uuid: UUID, trait_uuid: UUID) -> None:
        row = Database.session.get(TABLE_TypeTraits, (type_uuid, trait_uuid))
        if row is not None:
            Database.session.delete(row)


type_traits = TypeTraits()
