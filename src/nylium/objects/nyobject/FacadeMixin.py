# pyright: reportUninitializedInstanceVariable=false
# ``_uuid`` is declared here as the mixin's contract; NyObject.__init__
# (lifecycle.py) assigns it. Same pattern as the Row subclasses in tables/.
"""NyObject dataclass-like facade for UI rendering: fields snapshot,
to_dict/items and the value-semantics dunders."""
from __future__ import annotations

from collections.abc import ItemsView
from typing import cast, override
from uuid import UUID

from nylium.database import Database
from nylium.objects.NyProp import NyProp
from nylium.objects.NyType import NyType
from nylium.objects.NyTypeMeta import StoredValue, NyTypeMeta


class FacadeMixin:
    _uuid: UUID

    @classmethod
    @Database.use_same_session
    def fields(cls) -> dict[str, str]:
        """prop key -> value spec name, e.g. {'tags': 'Array<String>'}.
        ADR-0013: the effective schema — attached traits' props included,
        trait-bound values render as 'Any<TraitName>'."""
        owner = NyType.by_name(cls.__name__)
        if owner is None:
            return {}
        return {
            prop.key: prop.value_spec_name()
            for prop in NyProp.effective_for(owner)
        }

    def to_dict(self) -> dict[str, StoredValue]:
        """Snapshot of all props. Links come back as NyObject, arrays as lists."""
        return {key: cast(StoredValue, getattr(self, key)) for key in type(self).fields()}

    def items(self) -> ItemsView[str, StoredValue]:
        return self.to_dict().items()

    @override
    def __repr__(self) -> str:
        try:
            parts = ", ".join(
                f"{key}={getattr(self, key)!r}" for key in type(self).fields()
            )
        except AttributeError:
            return f"<{type(self).__name__} {self._uuid} (gone)>"
        return f"{type(self).__name__}({parts})"

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NyTypeMeta.root()):
            return NotImplemented
        return self._uuid == other.uuid

    @override
    def __hash__(self) -> int:
        return hash(self._uuid)
