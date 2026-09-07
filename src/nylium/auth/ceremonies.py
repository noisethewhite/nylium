"""WebAuthn ceremonies: register/login, start/finish."""
from __future__ import annotations

import json
from typing import ClassVar, cast
from uuid import UUID

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, options_to_json
from webauthn.helpers.structs import PublicKeyCredentialDescriptor

from nylium.tables import auth_challenges, auth_credentials, auth_users
from nylium.tables.auth_users import AuthUser
from nylium.system.environment import Environment

from .sessions import sessions


class ceremonies:
    """Namespace-only owner (snake_case by doctrine: groups behavior,
    never instantiated)."""

    RP_NAME: ClassVar[str] = "nylium"
    CHALLENGE_TTL_SECONDS: ClassVar[int] = 300

    # --- register ---

    @classmethod
    def register_start(
        cls, user_name: str | None, current_user_uuid: UUID | None
    ) -> str:
        """Open while zero credentials exist (first passkey = owner);
        afterwards requires a live session — adding keys = being logged in."""
        user_uuid = cls._register_subject(user_name, current_user_uuid)
        user = auth_users.get(user_uuid)
        if user is None:
            raise PermissionError("registration requires a session")
        known = auth_credentials.credential_ids_for(user_uuid)
        options = generate_registration_options(
            rp_id=str(Environment.rp_id),
            rp_name=cls.RP_NAME,
            user_id=user_uuid.bytes,
            user_name=user.name,
            exclude_credentials=[
                PublicKeyCredentialDescriptor(id=credential_id)
                for credential_id in known
            ],
        )
        auth_challenges.issue(
            options.challenge,
            auth_challenges.REGISTER_KIND,
            user_uuid,
            cls.CHALLENGE_TTL_SECONDS,
        )
        return options_to_json(options)

    @classmethod
    def register_finish(cls, body: str) -> str:
        """Verify a fresh passkey, store it, return a session token."""
        payload = cls._payload(body)
        challenge = cls._client_challenge(payload)
        ok, user_uuid = auth_challenges.consume(challenge, auth_challenges.REGISTER_KIND)
        if not ok or user_uuid is None:
            raise PermissionError("unknown or expired challenge")
        try:
            verification = verify_registration_response(
                credential=body,
                expected_challenge=challenge,
                expected_rp_id=str(Environment.rp_id),
                expected_origin=str(Environment.rp_origin),
            )
        except Exception as exc:
            raise PermissionError("passkey rejected") from exc
        auth_credentials.register(
            user_uuid,
            verification.credential_id,
            verification.credential_public_key,
            verification.sign_count,
            transports=cls._transports(payload),
        )
        return sessions.issue(user_uuid)

    # --- login ---

    @classmethod
    def login_start(cls) -> str:
        options = generate_authentication_options(rp_id=str(Environment.rp_id))
        auth_challenges.issue(
            options.challenge, auth_challenges.LOGIN_KIND, None, cls.CHALLENGE_TTL_SECONDS
        )
        return options_to_json(options)

    @classmethod
    def login_finish(cls, body: str) -> str:
        payload = cls._payload(body)
        credential_id = base64url_to_bytes(cls._string(payload, "rawId"))
        credential = auth_credentials.by_credential_id(credential_id)
        if credential is None:
            raise PermissionError("unknown credential")
        challenge = cls._client_challenge(payload)
        ok, _ = auth_challenges.consume(challenge, auth_challenges.LOGIN_KIND)
        if not ok:
            raise PermissionError("unknown or expired challenge")
        try:
            verification = verify_authentication_response(
                credential=body,
                expected_challenge=challenge,
                expected_rp_id=str(Environment.rp_id),
                expected_origin=str(Environment.rp_origin),
                credential_public_key=credential.public_key,
                credential_current_sign_count=credential.sign_count,
            )
        except Exception as exc:
            raise PermissionError("passkey rejected") from exc
        auth_credentials.mark_used(credential.uuid, verification.new_sign_count)
        return sessions.issue(credential.user_uuid)

    # --- internals ---

    @classmethod
    def _register_subject(
        cls, user_name: str | None, current_user_uuid: UUID | None
    ) -> UUID:
        if auth_credentials.count_all() == 0:
            if not user_name:
                raise TypeError("user name required for the first passkey")
            # Retry after an aborted ceremony reuses the orphaned user row.
            existing = next(AuthUser.name.foreach(user_name), None)
            if existing is not None:
                return existing.uuid
            return auth_users.create(user_name).uuid
        if current_user_uuid is None:
            raise PermissionError("registration requires a session")
        return current_user_uuid

    @classmethod
    def _payload(cls, body: str) -> dict[str, object]:
        try:
            parsed = cast(object, json.loads(body))
        except json.JSONDecodeError as exc:
            raise PermissionError("malformed credential payload") from exc
        if not isinstance(parsed, dict):
            raise PermissionError("malformed credential payload")
        return cast(dict[str, object], parsed)

    @classmethod
    def _string(cls, mapping: dict[str, object], key: str) -> str:
        value = mapping.get(key)
        if not isinstance(value, str):
            raise PermissionError("malformed credential payload")
        return value

    @classmethod
    def _nested(cls, mapping: dict[str, object], key: str) -> dict[str, object]:
        value = mapping.get(key)
        if not isinstance(value, dict):
            raise PermissionError("malformed credential payload")
        return cast(dict[str, object], value)

    @classmethod
    def _client_challenge(cls, payload: dict[str, object]) -> bytes:
        raw = base64url_to_bytes(cls._string(cls._nested(payload, "response"), "clientDataJSON"))
        try:
            client_data = cast(object, json.loads(raw))
        except json.JSONDecodeError as exc:
            raise PermissionError("malformed credential payload") from exc
        if not isinstance(client_data, dict):
            raise PermissionError("malformed credential payload")
        return base64url_to_bytes(cls._string(cast(dict[str, object], client_data), "challenge"))

    @classmethod
    def _transports(cls, payload: dict[str, object]) -> str:
        response = payload.get("response")
        if not isinstance(response, dict):
            return ""
        raw = cast(dict[str, object], response).get("transports")
        if not isinstance(raw, list):
            return ""
        return ",".join(
            item for item in cast(list[object], raw) if isinstance(item, str)
        )
