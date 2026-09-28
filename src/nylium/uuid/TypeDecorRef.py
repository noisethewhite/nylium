"""TypeDecorRef — typed reference to a ``TypeStyle`` row (``type_style``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import TypeStyle
from nylium.data.tables import type_style
from nylium.uuid.NyRef import NyRef


class TypeDecorRef(NyRef):
    """A ``type_style`` reference carrying its own table lookup."""

    @override
    def get(self) -> TypeStyle | None:
        """The ``TypeStyle`` row this reference points at, or ``None`` if it is gone."""
        return type_style.get(self._uuid)
