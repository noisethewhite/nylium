"""ObjectUUID — typed identifier for an ``Instance`` row (``instances``)."""
from __future__ import annotations

from typing import cast
from uuid import UUID

from pydantic_core import core_schema

import sqlalchemy as sqla
from sqlalchemy.orm import aliased

from nylium.database import Database
from nylium.database.Row import get_mapper
from nylium.data.rows import ArrayValue, Instance, InstanceLink, Prop, StringValue, Type, TypeStyle
from nylium.data.tables import instances


class ObjectUUID(UUID):
    """An ``instances`` uuid carrying its own table lookup and reverse
    projections (backlinks, array membership, tag chips)."""

    @classmethod
    def of(cls, value: UUID) -> "ObjectUUID":
        return cls(str(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.uuid_schema()

    def get(self) -> Instance | None:
        """The ``Instance`` row this uuid points at, or ``None`` if it is gone."""
        return instances.get(self)

    @classmethod
    @Database.use_same_session
    def instances_of_kind(cls, kind: str) -> list[ObjectUUID]:
        """Every instance uuid whose type has the given kind."""
        i_c = get_mapper(Instance).columns
        t_c = get_mapper(Type).columns
        rows: list[UUID] = list(
            Database.scalars(
                sqla.select(i_c.uuid)
                .join(Type, t_c.uuid == i_c.type_uuid)
                .where(t_c.kind == kind)
            ).all()
        )
        return [cls.of(u) for u in rows]

    @Database.use_same_session
    def array_link_uuids(self) -> list[ObjectUUID]:
        """Uuids of array-instance links held by this owner object."""
        iv_c = get_mapper(InstanceLink).columns
        p_c = get_mapper(Prop).columns
        t_c = get_mapper(Type).columns
        stmt = (
            sqla.select(iv_c.uuid)
            .join(Prop, iv_c.prop_uuid == p_c.uuid)
            .join(Type, p_c.value_type_uuid == t_c.uuid)
            .where(
                iv_c.inst_uuid == self,
                # mirrors NyType.ARRAY_TYPE_PREFIX (objects layer imports tables,
                # so the constant cannot flow the other way)
                t_c.name.like("Array<%"),
            )
        )
        rows: list[UUID] = list(Database.scalars(stmt).all())
        return [ObjectUUID.of(u) for u in rows]

    @Database.use_same_session
    def backlink_refs(self) -> list[tuple[ObjectUUID, str]]:
        """(owner uuid, owner type name) for every instance that points at
        this object — directly through a link prop or through membership in
        one of its arrays. Owners deduplicated, direct links first."""
        iv_c = get_mapper(InstanceLink).columns
        i_c = get_mapper(Instance).columns
        av_c = get_mapper(ArrayValue).columns

        direct_types = aliased(Type)
        direct = Database.execute(
            sqla.select(iv_c.inst_uuid, direct_types.name)
            .join(Instance, iv_c.inst_uuid == i_c.uuid)
            .join(direct_types, i_c.type_uuid == direct_types.uuid)
            .where(iv_c.uuid == self)
        ).all()

        box_link = aliased(InstanceLink)
        array_types = aliased(Type)
        via_arrays = Database.execute(
            sqla.select(box_link.inst_uuid, array_types.name)
            .select_from(ArrayValue)
            .join(box_link, av_c.inst_uuid == box_link.uuid)
            .join(Instance, box_link.inst_uuid == i_c.uuid)
            .join(array_types, i_c.type_uuid == array_types.uuid)
            .where(av_c.value_uuid == self)
        ).all()

        seen: set[ObjectUUID] = set()
        refs: list[tuple[ObjectUUID, str]] = []
        for r in [*direct, *via_arrays]:
            owner_uuid = ObjectUUID.of(cast(UUID, r[0]))
            if owner_uuid in seen:
                continue
            seen.add(owner_uuid)
            refs.append((owner_uuid, cast(str, r[1])))
        # deterministic wire order: SQL row order is an implementation detail
        return sorted(refs, key=lambda item: (item[1], str(item[0])))

    @Database.use_same_session
    def array_tag_rows(
        self, array_type_name: str, name_prop_key: str
    ) -> list[tuple[ObjectUUID, str, str, str | None, str]]:
        """ADR-0005 reverse projection: every array that holds this object as
        a member of an ``Array<array_type_name>`` prop, with enough info to
        paint a tag chip — (owner uuid, prop key, registry name, display
        name, owner type color). One query, no N+1."""
        name_prop = aliased(Prop)
        owner_types = aliased(Type)
        owner_decor = aliased(TypeStyle)
        av_c = get_mapper(ArrayValue).columns
        iv_c = get_mapper(InstanceLink).columns
        p_c = get_mapper(Prop).columns
        i_c = get_mapper(Instance).columns
        s_c = get_mapper(StringValue).columns
        t_c = get_mapper(Type).columns
        rows = Database.execute(
            sqla.select(
                iv_c.inst_uuid,
                p_c.key,
                i_c.name,
                s_c.value,
                owner_decor.color,
            )
            .select_from(ArrayValue)
            .join(InstanceLink, iv_c.uuid == av_c.inst_uuid)
            .join(Prop, p_c.uuid == iv_c.prop_uuid)
            .join(Type, t_c.uuid == p_c.value_type_uuid)
            .join(Instance, i_c.uuid == iv_c.inst_uuid)
            .join(owner_types, owner_types.uuid == i_c.type_uuid)
            .join(owner_decor, owner_decor.uuid == owner_types.uuid)
            .join(name_prop, name_prop.owner_type_uuid == i_c.type_uuid)
            .join(
                StringValue,
                sqla.and_(
                    s_c.inst_uuid == i_c.uuid,
                    s_c.prop_uuid == name_prop.uuid,
                ),
                isouter=True,
            )
            .where(
                av_c.value_uuid == self,
                t_c.name == array_type_name,
                name_prop.key == name_prop_key,
            )
            .distinct()
        ).all()
        return [
            (
                ObjectUUID.of(cast(UUID, r[0])),
                cast(str, r[1]),
                cast(str, r[2]),
                cast("str | None", r[3]),
                cast(str, r[4]),
            )
            for r in rows
        ]

    @Database.use_same_session
    def delete_memberships(self) -> None:
        """Drop every array-membership row pointing at this element uuid."""
        c = get_mapper(ArrayValue).columns
        _ = Database.execute(sqla.delete(ArrayValue).where(c.value_uuid == self))

    @Database.use_same_session
    def link_for(self, prop_uuid: UUID) -> InstanceLink | None:
        """The link row held by (this owner, prop), or None."""
        c = get_mapper(InstanceLink).columns
        return Database.scalar(
            sqla.select(InstanceLink).where(c.inst_uuid == self, c.prop_uuid == prop_uuid)
        )

    @Database.use_same_session
    def merge_link(self, prop_uuid: UUID, target_uuid: UUID) -> None:
        """Insert-or-replace the link row for (this owner, prop) pointing at
        the given target uuid (ADR-0028)."""
        _ = Database.merge(
            InstanceLink(uuid=target_uuid, prop_uuid=prop_uuid, inst_uuid=self)
        )

    @Database.use_same_session
    def add_link(self, prop_uuid: UUID, target_uuid: UUID) -> None:
        """Insert a brand-new link row and flush (plain insert, ADR-0028)."""
        Database.add(InstanceLink(uuid=target_uuid, prop_uuid=prop_uuid, inst_uuid=self))
        Database.flush()

    @Database.use_same_session
    def delete_links_to(self) -> None:
        """Delete every link row whose target is this instance uuid."""
        c = get_mapper(InstanceLink).columns
        _ = Database.execute(sqla.delete(InstanceLink).where(c.uuid == self))

    @classmethod
    def delete_link(cls, row: InstanceLink) -> None:
        """Delete the given link row (already fetched by the caller)."""
        Database.delete(row)
