# pyright: reportUninitializedInstanceVariable=false
# ``_uuid`` is declared here as the mixin's contract; WObject.__init__
# (lifecycle.py) assigns it. Same pattern as the Row subclasses in tables/.
"""WObject dataclass-like facade for UI rendering: fields snapshot,
to_dict/items and the value-semantics dunders."""
from __future__ import annotations

from collections.abc import ItemsView
from typing import cast, override
from uuid import UUID

from nylium.database import databasemethod
from nylium.objects.wprop import WProp
from nylium.objects.wtype import WType
from nylium.objects.wtypemeta import StoredValue, WTypeMeta


class FacadeMixin:
    _uuid: UUID

    @classmethod
    @databasemethod(commit=False)
    def fields(cls) -> dict[str, str]:
        """prop key -> value spec name, e.g. {'tags': 'Array<String>'}.
        ADR-0013: the effective schema — attached traits' props included,
        trait-bound values render as 'Any<TraitName>'."""
        owner = WType.by_name(cls.__name__)
        if owner is None:
            return {}
        return {
            prop.key: prop.value_spec_name()
            for prop in WProp.effective_for(owner)
        }

    def to_dict(self) -> dict[str, StoredValue]:
        """Snapshot of all props. Links come back as WObject, arrays as lists."""
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
        if not isinstance(other, WTypeMeta.root()):
            return NotImplemented
        return self._uuid == other.uuid

    @override
    def __hash__(self) -> int:
        return hash(self._uuid)
