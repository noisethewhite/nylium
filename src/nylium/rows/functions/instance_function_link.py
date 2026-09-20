# pyright: reportUninitializedInstanceVariable=false
# Row.__init__ copies every mapped column into the instance dynamically;
# the bare annotations below are the schema, not a constructor signature.
"""One function binding: a snapshot of a TABLE_InstanceFunctionLinks row."""
from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from nylium.database.table import Row
from nylium.tables.functions.instance_function_links import TABLE_InstanceFunctionLinks


class InstanceFunctionLink(Row):
    """One function binding: a snapshot of a TABLE_InstanceFunctionLinks row."""

    __table__: ClassVar[type[object]] = TABLE_InstanceFunctionLinks

    inst_uuid: UUID
    prop_uuid: UUID
    function_uuid: UUID
