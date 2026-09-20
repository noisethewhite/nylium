# pyright: reportUninitializedInstanceVariable=false
# ``_uuid`` is declared here as the mixin's contract; WObject.__init__
# (lifecycle.py) assigns it. Same pattern as the Row subclasses in tables/.
"""WObject persistence — read/write of prop values.

Owns the mapping between python-level values and the prop-value rows.
ADR-0019 / ADR-0030: this module decides *what* to store; every statement
lives in the ``nylium.objects`` helpers (wlink/wfile) — no ``sqla`` /
``Database`` imports here.
"""
from __future__ import annotations

from uuid import UUID

from nylium.objects.wprop import WProp
from nylium.objects.wscalar import ScalarPayload, WScalar
from nylium.objects.wtypemeta import WObjectShape
from nylium.objects.wfile import file_ref_for, write_ref
from nylium.objects.wlink import link_for, merge_link
from nylium.tables.values.instance_values import TABLE_InstanceValues


class PersistenceMixin:
    """Read and write prop values for an instance; uuid bookkeeping is upstream."""

    _uuid: UUID

    def _link(self, prop: WProp) -> TABLE_InstanceValues | None:
        return link_for(self._uuid, prop.uuid)

    def _file_ref(self, prop: WProp) -> UUID | None:
        return file_ref_for(self._uuid, prop.uuid)

    def _write_scalar(
        self, prop: WProp, scalar: type[WScalar], value: ScalarPayload | None
    ) -> None:
        # clearing a scalar removes the row — a NULL row violates the
        # table's NOT NULL constraint and reads back as None anyway
        if value is None:
            _ = scalar.SCALAR.clear(self._uuid, prop.uuid)
            return
        scalar.SCALAR.write(self._uuid, prop.uuid, scalar.to_storage(value))

    def _write_link(self, prop: WProp, value: WObjectShape) -> None:
        merge_link(value.uuid, prop.uuid, self._uuid)

    def _write_file_ref(self, prop: WProp, value: UUID | None) -> None:
        write_ref(self._uuid, prop.uuid, value)
