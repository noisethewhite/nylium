"""Nylium-style object model as SQL tables.

Mirrors nylium ADR-008: user-defined types with kind-spec schemas, a global
relation registry, notes with free-form props, and UUID links between notes.

Design notes:
- Link-typed fields are normalized into the `links` table; `notes.props`
  keeps only scalar/select/tag values.
- Backlinks are NOT stored: they are a query over `links.target_id`
  (same as nylium's find_referrers, but indexed and free).
- Union links (link<Person|Human>) need no schema change — the target is
  always a note UUID, the allowed-type set is validated app-side.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Type(Base):
    """A user-defined note type (one types.yaml entry)."""

    __tablename__ = "types"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(Text, unique=True)  # "Person", "Human", ...
    name: Mapped[str] = mapped_column(Text)              # display label
    schema_: Mapped[dict] = mapped_column("schema", JSONB)  # field -> resolved kind-spec
    featured: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)  # header field order
    options: Mapped[dict] = mapped_column(JSONB, default=dict)              # select options per field

    notes: Mapped[list["Note"]] = relationship(back_populates="type")


class Relation(Base):
    """A globally reusable field definition (relations.yaml entry)."""

    __tablename__ = "relations"

    key: Mapped[str] = mapped_column(Text, primary_key=True)  # "@key" in types.yaml resolves here
    name: Mapped[str | None] = mapped_column(Text)            # display label, defaults to key
    format: Mapped[str] = mapped_column(Text)                 # kind-spec: "text", "date?", "select", ...
    options: Mapped[list[str] | None] = mapped_column(ARRAY(Text))  # only for format == "select"


class Note(Base):
    """A note: typed object with free-form props and system dates."""

    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("types.id"))
    title: Mapped[str] = mapped_column(Text)
    props: Mapped[dict] = mapped_column(JSONB, default=dict)  # scalar/select/tag values only
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    type: Mapped[Type] = relationship(back_populates="notes")
    outgoing_links: Mapped[list["Link"]] = relationship(
        back_populates="source", foreign_keys="Link.source_id"
    )
    backlinks: Mapped[list["Link"]] = relationship(
        back_populates="target", foreign_keys="Link.target_id"
    )


class Link(Base):
    """A UUID reference from one note to another, under a relation key."""

    __tablename__ = "links"
    __table_args__ = (
        UniqueConstraint("source_id", "relation_key", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notes.id"))
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notes.id"))
    relation_key: Mapped[str] = mapped_column(Text)  # which field holds this link
    position: Mapped[int] = mapped_column(default=0)  # order within list-valued link fields

    source: Mapped[Note] = relationship(back_populates="outgoing_links", foreign_keys=[source_id])
    target: Mapped[Note] = relationship(back_populates="backlinks", foreign_keys=[target_id])
