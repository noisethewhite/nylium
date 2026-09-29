"""UserRef — typed reference to an ``AuthUser`` row (``auth_users``)."""
from __future__ import annotations

from typing import override

from nylium.data.rows import (
    AuthUser,
    UnitPart,
    TypeStyle,
    TraitStyle,
    ApiToken,
    FunctionNode,
    FunctionEdge,
    File,
    EnumOption,
    AuthCredential
)
from nylium.data.tables import (
    auth_users,
    unit_parts,
    type_style,
    trait_style,
    api_tokens,
    function_nodes,
    function_edges,
    files,
    enum_options,
    auth_credentials
)
from nylium.abc import NyRef


class CredentialRef(NyRef):
    """A ``auth_credentials`` reference carrying its own table lookup."""

    @override
    def get(self) -> AuthCredential | None:
        """The ``AuthCredential`` row this reference points at, or ``None`` if it is gone."""
        return auth_credentials.get(self._uuid)


class EnumOptionRef(NyRef):
    """A ``enum_options`` reference carrying its own table lookup."""

    @override
    def get(self) -> EnumOption | None:
        """The ``EnumOption`` row this reference points at, or ``None`` if it is gone."""
        return enum_options.get(self._uuid)


class FileRef(NyRef):
    """A ``files`` reference carrying its own table lookup."""

    @override
    def get(self) -> File | None:
        """The ``File`` row this reference points at, or ``None`` if it is gone."""
        return files.get(self._uuid)


class FunctionEdgeRef(NyRef):
    """A ``function_edges`` reference carrying its own table lookup."""

    @override
    def get(self) -> FunctionEdge | None:
        """The ``FunctionEdge`` row this reference points at, or ``None`` if it is gone."""
        return function_edges.get(self._uuid)


class FunctionRef(NyRef):
    """A ``function_nodes`` reference carrying its own table lookup."""

    @override
    def get(self) -> FunctionNode | None:
        """The ``FunctionNode`` row this reference points at, or ``None`` if it is gone."""
        return function_nodes.get(self._uuid)


class TokenRef(NyRef):
    """A ``api_tokens`` reference carrying its own table lookup."""

    @override
    def get(self) -> ApiToken | None:
        """The ``ApiToken`` row this reference points at, or ``None`` if it is gone."""
        return api_tokens.get(self._uuid)


class TraitDecorRef(NyRef):
    """A ``trait_style`` reference carrying its own table lookup."""

    @override
    def get(self) -> TraitStyle | None:
        """The ``TraitStyle`` row this reference points at, or ``None`` if it is gone."""
        return trait_style.get(self._uuid)


class TypeDecorRef(NyRef):
    """A ``type_style`` reference carrying its own table lookup."""

    @override
    def get(self) -> TypeStyle | None:
        """The ``TypeStyle`` row this reference points at, or ``None`` if it is gone."""
        return type_style.get(self._uuid)


class UnitPartRef(NyRef):
    """A ``unit_parts`` reference carrying its own table lookup."""

    @override
    def get(self) -> UnitPart | None:
        """The ``UnitPart`` row this reference points at, or ``None`` if it is gone."""
        return unit_parts.get(self._uuid)


class UserRef(NyRef):
    """An ``auth_users`` reference carrying its own table lookup."""

    @override
    def get(self) -> AuthUser | None:
        """The ``AuthUser`` row this reference points at, or ``None`` if it is gone."""
        return auth_users.get(self._uuid)
