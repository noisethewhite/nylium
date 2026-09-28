"""EnumOptionUUID — typed reference to a ``EnumOption`` row (``enum_options``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import EnumOption
from nylium.data.tables import enum_options
from nylium.uuid.NyRef import NyRef


class EnumOptionUUID(NyRef):
    """A ``enum_options`` reference carrying its own table lookup."""

    @override
    def get(self) -> EnumOption | None:
        """The ``EnumOption`` row this reference points at, or ``None`` if it is gone."""
        return enum_options.get(self._uuid)
