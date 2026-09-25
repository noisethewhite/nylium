"""TypeUUID — typed identifier for a ``Type`` row (``types``)."""
from __future__ import annotations

from uuid import UUID

from nylium.data.rows import EnumOption, Prop, Type, UnitPart
from nylium.data.tables import (
    enum_options,
    props,
    traits,
    type_decor,
    type_traits,
    types,
    unit_parts,
)


class TypeUUID(UUID):
    """A ``types`` uuid carrying its own table lookup and schema navigation."""

    @classmethod
    def of(cls, value: UUID) -> "TypeUUID":
        return cls(str(value))

    def get(self) -> Type | None:
        """The ``Type`` row this uuid points at, or ``None`` if it is gone."""
        return types.get(self)

    def effective_props(self) -> list[Prop]:
        """The effective schema (ADR-0013): own props, then each attached
        trait's props in attach order."""
        result = sorted(props.where(owner_type_uuid=self), key=lambda p: p.position)
        for trait_uuid in type_traits.attached_trait_uuids(self):
            result.extend(
                sorted(props.where(owner_trait_uuid=trait_uuid), key=lambda p: p.position)
            )
        return result

    def plural_name(self) -> str:
        return type_decor[self].plural_name

    def icon(self) -> str:
        return type_decor[self].icon

    def color(self) -> str:
        return type_decor[self].color

    def trait_names(self) -> list[str]:
        """Names of traits attached to this type, in attach order."""
        result: list[str] = []
        for link in sorted(type_traits.where(type_uuid=self), key=lambda link: link.position):
            trait = traits.get(link.trait_uuid)
            if trait is not None:
                result.append(trait.name)
        return result

    def enum_options(self) -> list[EnumOption]:
        return sorted(enum_options.where(type_uuid=self), key=lambda o: o.position)

    def unit_parts(self) -> list[UnitPart]:
        return sorted(unit_parts.where(type_uuid=self), key=lambda p: p.position)

    def name_of(self) -> str:
        """The type's name, or ``<dangling>`` if the type row is gone."""
        t = types.get(self)
        return "<dangling>" if t is None else t.name
