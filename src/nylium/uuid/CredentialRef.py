"""CredentialRef — typed reference to a ``AuthCredential`` row (``auth_credentials``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import AuthCredential
from nylium.data.tables import auth_credentials
from nylium.uuid.NyRef import NyRef


class CredentialRef(NyRef):
    """A ``auth_credentials`` reference carrying its own table lookup."""

    @override
    def get(self) -> AuthCredential | None:
        """The ``AuthCredential`` row this reference points at, or ``None`` if it is gone."""
        return auth_credentials.get(self._uuid)
