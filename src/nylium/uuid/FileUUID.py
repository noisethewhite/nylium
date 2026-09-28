"""FileUUID — typed reference to a ``File`` row (``files``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import File
from nylium.data.tables import files
from nylium.uuid.NyRef import NyRef


class FileUUID(NyRef):
    """A ``files`` reference carrying its own table lookup."""

    @override
    def get(self) -> File | None:
        """The ``File`` row this reference points at, or ``None`` if it is gone."""
        return files.get(self._uuid)
