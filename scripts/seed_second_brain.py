"""Seed the personal second-brain domain types (ADR-0009, section 1).

Idempotent and additive: skips types/enums that already exist, and for an
existing object type it ADDS any missing props (via WProp.ensure) without
touching or deleting props the user already has — so re-running against a
live database never destroys data. Domain types are DATA, not code: they
are created through the same Api facade the UI uses, never baked into the
engine (see ADR-0009).

Run on the prod host AFTER the server has booted once (its boot creates the
tables). DATABASE_URL / RP_ID / RP_ORIGIN / FILES_DIR must be exported — the
app reads them via nylium.system.Environment:
    uv run python scripts/seed_second_brain.py
"""
from __future__ import annotations

# Composition root: import first to break the import cycle that
# `from nylium.api import Api` alone would trigger.
from nylium.server import NyliumApp as _NyliumApp  # pyright: ignore[reportUnusedImport]
from nylium.api import Api
from nylium.objects.wprop import WProp
from nylium.objects.wtype import WType


def ensure_enum(name: str, options: list[str]) -> None:
    if WType.by_name(name) is not None:
        print(f"skip {name!r} (already exists)")
        return
    _ = Api.create_enum(name, options)
    print(f"created enum {name!r}: {options}")


def ensure_type(name: str, props: dict[str, str], plural_name: str) -> None:
    owner = WType.by_name(name)
    if owner is None:
        _ = Api.create_type(name, props, plural_name=plural_name)
        print(f"created type {name!r}: {list(props)}")
        return
    existing = {prop.key for prop in WProp.all_for(owner)}
    added: list[str] = []
    base = len(existing)
    for key, value_type_name in props.items():
        if key in existing:
            continue
        _ = WProp.ensure(owner, key, WType.ensure(value_type_name), position=base + len(added))
        added.append(key)
    if added:
        print(f"extended type {name!r}: added {added}")
    else:
        print(f"skip {name!r} (exists, complete)")


def main() -> None:
    ensure_enum("TaskStatus", ["todo", "doing", "done"])
    ensure_enum("Priority", ["low", "medium", "high"])

    ensure_type(
        "Task",
        {
            "name": "String",
            "status": "TaskStatus",
            "priority": "Priority",
            "due": "Date",
            "tags": "Array<String>",
            "notes": "String",
        },
        "Tasks",
    )

    ensure_type(
        "Event",
        {
            "name": "String",
            "start": "Datetime",
            "end": "Datetime",
            "location": "String",
            "notes": "String",
        },
        "Events",
    )

    ensure_type(
        "Note",
        {
            "name": "String",
            "body": "String",
            "tags": "Array<String>",
            "category": "String",
        },
        "Notes",
    )

    ensure_type(
        "Person",
        {
            "name": "String",
            "role": "String",
            "contact": "String",
            "notes": "String",
        },
        "People",
    )

    print("seed complete.")


if __name__ == "__main__":
    main()
