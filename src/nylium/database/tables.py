from typing import ClassVar
from uuid import UUID, uuid4
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import sqlalchemy as sqla
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    LargeBinary,
    Text,
    Time,
    UniqueConstraint,
    func,
    Integer,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from nylium.database.database import Database


class Base(DeclarativeBase):
    pass


class Types(Base):
    __tablename__: str = "types"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # NULL for builtins and array types — only user types carry both forms
    plural_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def name_by_uuid(cls, session: Session, uuid: UUID) -> str | None:
        row = session.get(cls, uuid)
        return None if row is None else row.name

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def uuid_by_name(cls, session: Session, name: str) -> UUID | None:
        row = session.scalar(
            sqla.select(cls).where(
                cls.name == name
            )
        )
        return None if row is None else row.uuid

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def all_names(cls, session: Session) -> list[str]:
        return list(session.scalars(sqla.select(cls.name)).all())

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def delete_by_uuid(cls, session: Session, uuid: UUID) -> None:
        row = session.get(cls, uuid)
        if row is not None:
            session.delete(row)  # its props cascade


class Props(Base):
    __tablename__: str = "props"
    __table_args__: tuple[UniqueConstraint, ...] = (
        # One key can't be defined twice on the same owner type
        UniqueConstraint("owner_type_uuid", "key"),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    owner_type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid", ondelete="CASCADE"), nullable=False
    )
    value_type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid"), nullable=False
    )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def get_type_name(cls, session: Session, owner_type_uuid: UUID, key: str) -> str:
        row = session.scalar(
            sqla.select(cls).where(
                cls.owner_type_uuid == owner_type_uuid, cls.key == key
            )
        )
        if row is None:
            raise KeyError(f"type {Types.name_by_uuid(owner_type_uuid)!r} has no prop {key!r}")
        value_type = Types.name_by_uuid(row.value_type_uuid)
        if value_type is None:
            raise KeyError(f"Type with UUID {row.value_type_uuid} does not exist")
        return value_type


# Instances of types
# (Both arrays and scalars are considered types, too)
class Instances(Base):
    __tablename__: str = "instances"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    type_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("types.uuid"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def get_type_name(cls, session: Session, uuid: UUID) -> str:
        inst = session.get(cls, uuid)
        if inst is None:
            return "<gone>"
        name = Types.name_by_uuid(inst.type_uuid)
        return "<dangling>" if name is None else name

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def exists(cls, session: Session, uuid: UUID) -> bool:
        return session.get(cls, uuid) is not None

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def type_uuid_of(cls, session: Session, uuid: UUID) -> UUID | None:
        inst = session.get(cls, uuid)
        return None if inst is None else inst.type_uuid

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def uuids_of_type(cls, session: Session, type_uuid: UUID) -> list[UUID]:
        return list(
            session.scalars(
                sqla.select(cls.uuid).where(cls.type_uuid == type_uuid)
            ).all()
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def count_of_type(cls, session: Session, type_uuid: UUID) -> int:
        return session.scalar(
            sqla.select(sqla.func.count())
            .select_from(cls)
            .where(cls.type_uuid == type_uuid)
        ) or 0

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def register(cls, session: Session, uuid: UUID, type_uuid: UUID, name: str) -> None:
        session.add(cls(uuid=uuid, type_uuid=type_uuid, name=name))


# === Values ===
# Scalars live in one table per value kind, keyed by (instance, prop).
# No row = the prop has no value on that instance.

class StringValues(Base):
    __tablename__: str = "string_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)


class IntegerValues(Base):
    __tablename__: str = "integer_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)


class NumericValues(Base):
    __tablename__: str = "numeric_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[Decimal] = mapped_column(nullable=False)


class BooleanValues(Base):
    __tablename__: str = "boolean_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[bool] = mapped_column(nullable=False)


class DatetimeValues(Base):
    __tablename__: str = "datetime_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DateValues(Base):
    __tablename__: str = "date_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[date] = mapped_column(Date, nullable=False)


class TimeValues(Base):
    __tablename__: str = "time_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[time] = mapped_column(Time, nullable=False)


# Year-less calendar stamps (MonthDay/MonthDayTime) have no native
# column type — they cross the boundary as their text stamp form.
class MonthDayValues(Base):
    __tablename__: str = "monthday_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)


class MonthDayTimeValues(Base):
    __tablename__: str = "monthdaytime_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)


# Values that are references to other instances (links, nested objects,
# arrays). The referenced instance's own uuid doubles as this row's pk.
class InstanceValues(Base):
    __tablename__: str = "instance_values"

    uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), primary_key=True
    )
    prop_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("props.uuid", ondelete="CASCADE"), nullable=False
    )
    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), nullable=False
    )


# Array elements: the array itself is an instance (of an array type);
# rows map (array instance, index) -> element instance.
class ArrayValues(Base):
    __tablename__: str = "array_values"

    inst_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid", ondelete="CASCADE"), primary_key=True
    )
    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("instances.uuid"), nullable=False
    )


# === Auth ===
# Passkey (WebAuthn) infrastructure. System tables like Instances/Types,
# deliberately NOT nylium objects: auth sits below the object layer, and
# the type system has no blob scalar for public keys / credential IDs.

class AuthUsers(Base):
    __tablename__: str = "auth_users"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def create(cls, session: Session, name: str) -> "AuthUsers":
        user = cls(name=name)
        session.add(user)
        session.flush()  # populate uuid/created_at before the session ends
        return user

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_uuid(cls, session: Session, uuid: UUID) -> "AuthUsers | None":
        return session.get(cls, uuid)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_name(cls, session: Session, name: str) -> "AuthUsers | None":
        return session.scalar(sqla.select(cls).where(cls.name == name))


class AuthCredentials(Base):
    __tablename__: str = "auth_credentials"

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=False
    )
    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, unique=True
    )
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transports: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def count_all(cls, session: Session) -> int:
        return session.scalar(sqla.select(sqla.func.count()).select_from(cls)) or 0

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_credential_id(
        cls, session: Session, credential_id: bytes
    ) -> "AuthCredentials | None":
        return session.scalar(
            sqla.select(cls).where(cls.credential_id == credential_id)
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def credential_ids_for(cls, session: Session, user_uuid: UUID) -> list[bytes]:
        return list(
            session.scalars(
                sqla.select(cls.credential_id).where(cls.user_uuid == user_uuid)
            ).all()
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def register(
        cls,
        session: Session,
        user_uuid: UUID,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
        transports: str,
    ) -> None:
        session.add(
            cls(
                user_uuid=user_uuid,
                credential_id=credential_id,
                public_key=public_key,
                sign_count=sign_count,
                transports=transports,
            )
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def mark_used(cls, session: Session, uuid: UUID, sign_count: int) -> None:
        row = session.get(cls, uuid)
        if row is not None:
            row.sign_count = sign_count
            row.last_used_at = datetime.now(timezone.utc)


class AuthChallenges(Base):
    """One-shot WebAuthn challenges. Consumed on use, dead after TTL."""
    __tablename__: str = "auth_challenges"

    REGISTER_KIND: ClassVar[str] = "register"
    LOGIN_KIND: ClassVar[str] = "login"

    challenge: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    user_uuid: Mapped[UUID | None] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def issue(
        cls,
        session: Session,
        challenge: bytes,
        kind: str,
        user_uuid: UUID | None,
        ttl_seconds: int,
    ) -> None:
        cls.purge_expired()
        session.add(
            cls(
                challenge=challenge,
                kind=kind,
                user_uuid=user_uuid,
                expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=ttl_seconds),
            )
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def consume(
        cls, session: Session, challenge: bytes, kind: str
    ) -> tuple[bool, UUID | None]:
        """Pop a challenge row: valid only if it exists, matches the
        ceremony kind and has not expired. One use, then gone.
        Returns (valid, user_uuid bound at issue time — None for login)."""
        row = session.get(cls, challenge)
        if row is None:
            return False, None
        user_uuid = row.user_uuid
        alive = row.expires_at > datetime.now(timezone.utc)
        _ = session.execute(sqla.delete(cls).where(cls.challenge == challenge))
        if row.kind != kind or not alive:
            return False, None
        return True, user_uuid

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def purge_expired(cls, session: Session) -> None:
        _ = session.execute(
            sqla.delete(cls).where(cls.expires_at <= datetime.now(timezone.utc))
        )


class AuthSessions(Base):
    """Server-side sessions: the cookie carries a random token, the table
    stores only its sha256 — a leaked dump yields no usable tokens."""
    __tablename__: str = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("auth_users.uuid", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def create(
        cls, session: Session, user_uuid: UUID, token_hash: str, expires_at: datetime
    ) -> None:
        session.add(
            cls(token_hash=token_hash, user_uuid=user_uuid, expires_at=expires_at)
        )

    @classmethod
    @Database.sessionmethod(bundled=False, commit=False)
    def by_hash(cls, session: Session, token_hash: str) -> "AuthSessions | None":
        return session.get(cls, token_hash)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def refresh(cls, session: Session, token_hash: str, expires_at: datetime) -> None:
        row = session.get(cls, token_hash)
        if row is not None:
            row.expires_at = expires_at

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def delete(cls, session: Session, token_hash: str) -> None:
        row = session.get(cls, token_hash)
        if row is not None:
            session.delete(row)

    @classmethod
    @Database.sessionmethod(bundled=False, commit=True)
    def purge_expired(cls, session: Session) -> None:
        _ = session.execute(
            sqla.delete(cls).where(cls.expires_at <= datetime.now(timezone.utc))
        )
