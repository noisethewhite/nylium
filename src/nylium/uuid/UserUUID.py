"""UserUUID — typed reference to an ``AuthUser`` row (``auth_users``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import AuthUser
from nylium.data.tables import auth_users
from nylium.uuid.NyRef import NyRef


class UserUUID(NyRef):
    """An ``auth_users`` reference carrying its own table lookup."""

    @override
    def get(self) -> AuthUser | None:
        """The ``AuthUser`` row this reference points at, or ``None`` if it is gone."""
        return auth_users.get(self._uuid)
