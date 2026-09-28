"""TokenUUID — typed reference to a ``ApiToken`` row (``api_tokens``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import ApiToken
from nylium.data.tables import api_tokens
from nylium.uuid.NyRef import NyRef


class TokenUUID(NyRef):
    """A ``api_tokens`` reference carrying its own table lookup."""

    @override
    def get(self) -> ApiToken | None:
        """The ``ApiToken`` row this reference points at, or ``None`` if it is gone."""
        return api_tokens.get(self._uuid)
