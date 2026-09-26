# pyright: reportUninitializedInstanceVariable=false
# ``_uuid`` is declared here as the mixin's contract; NyObject.__init__
# (lifecycle.py) assigns it. Same pattern as the Row subclasses in tables/.
"""NyObject persistence — read/write of prop values.

Owns the mapping between python-level values and the prop-value rows.
ADR-0019 / ADR-0030: this module decides *what* to store; every statement
lives in the ``nylium.ny`` helpers (wlink/nyfile) — no ``sqla`` /
``Database`` imports here.
"""
from __future__ import annotations

from uuid import UUID

from nylium.ny.NyProp import NyProp
from nylium.ny.NyScalar import NyScalar
from nylium.ny.NyScalar import ScalarPayload
from nylium.ny.NyObjectProtocol import NyObjectProtocol
from nylium.data.rows import InstanceLink
from nylium.uuid import FileUUID, ObjectUUID


class PersistenceMixin:
    """Read and write prop values for an instance; uuid bookkeeping is upstream."""

    _uuid: ObjectUUID

    def _link(self, prop: NyProp) -> InstanceLink | None:
        return self._uuid.link_for(prop.uuid)

    def _file_ref(self, prop: NyProp) -> UUID | None:
        return FileUUID.ref_for(self._uuid, prop.uuid)

    def _write_scalar(
        self, prop: NyProp, scalar: type[NyScalar], value: ScalarPayload | None
    ) -> None:
        # clearing a scalar removes the row — a NULL row violates the
        # table's NOT NULL constraint and reads back as None anyway
        if value is None:
            _ = scalar.SCALAR.clear(self._uuid, prop.uuid)
            return
        scalar.SCALAR.write(self._uuid, prop.uuid, scalar.to_storage(value))

    def _write_link(self, prop: NyProp, value: NyObjectProtocol) -> None:
        self._uuid.merge_link(prop.uuid, value.uuid)

    def _write_file_ref(self, prop: NyProp, value: UUID | None) -> None:
        FileUUID.write_ref(self._uuid, prop.uuid, value)
