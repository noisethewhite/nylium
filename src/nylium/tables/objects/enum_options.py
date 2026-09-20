# pyright: reportImportCycles=false
# Row navigation is bidirectional by design (Type.props <-> Prop.value_type);
# the back-edges are lazy function-level imports, so there is no runtime cycle.
"""The enum_options table as a Mapping of writable options (Table class + singleton)."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

import sqlalchemy as sqla

from nylium.database import Database, commit_after_this, use_same_session
from nylium.database.table import Row, Table
from nylium.tables.objects.enum_option import EnumOption as EnumOption
from nylium.tables.objects.props import TABLE_Props as TABLE_Props
from nylium.tables.objects.table_enum_options import TABLE_EnumOptions as TABLE_EnumOptions
from nylium.tables.values.string_values import TABLE_StringValues as TABLE_StringValues


class EnumOptions(Table[UUID, EnumOption]):
    """The enum_options table as a Mapping of writable options."""

    __row__: ClassVar[type[Row]] = EnumOption

    @use_same_session
    def count_usage(self, type_uuid: UUID, value: str) -> int:
        """How many stored prop values currently equal this option."""
        return int(
            Database.scalar(
                sqla.select(sqla.func.count())
                .select_from(TABLE_StringValues)
                .join(TABLE_Props, TABLE_StringValues.prop_uuid == TABLE_Props.uuid)
                .where(
                    TABLE_Props.value_type_uuid == type_uuid,
                    TABLE_StringValues.value == value,
                )
            )
            or 0
        )

    @commit_after_this
    def sync(self, type_uuid: UUID, items: list[tuple[UUID | None, str]]) -> None:
        """Apply the editor's full option draft, mirroring Props.sync_schema:
        a matching uuid renames the option in place (the rename rewrites
        stored string_values), None creates, omitted options are deleted —
        but a delete refuses while the option is still in use."""
        existing = {
            row.uuid: row
            for row in Database.scalars(
                sqla.select(TABLE_EnumOptions).where(
                    TABLE_EnumOptions.type_uuid == type_uuid
                )
            )
        }
        kept = {uuid for uuid, _ in items if uuid is not None}
        for stale_uuid, stale_row in existing.items():
            if stale_uuid in kept:
                continue
            usage = self.count_usage(type_uuid, stale_row.value)
            if usage:
                raise ValueError(
                    f"option {stale_row.value!r} is still used by {usage} values"
                )
            Database.delete(stale_row)
        Database.flush()
        for position, (option_uuid, value) in enumerate(items):
            if option_uuid is None or option_uuid not in existing:
                Database.add(
                    TABLE_EnumOptions(
                        uuid=uuid4(),
                        type_uuid=type_uuid,
                        value=value,
                        position=position,
                    )
                )
                continue
            row = existing[option_uuid]
            if row.value != value:
                _ = Database.execute(
                    sqla.update(TABLE_StringValues)
                    .where(
                        TABLE_StringValues.value == row.value,
                        TABLE_StringValues.prop_uuid.in_(
                            sqla.select(TABLE_Props.uuid).where(
                                TABLE_Props.value_type_uuid == type_uuid
                            )
                        ),
                    )
                    .values(value=value)
                )
                row.value = value
            row.position = position
        Database.flush()


enum_options = EnumOptions()
