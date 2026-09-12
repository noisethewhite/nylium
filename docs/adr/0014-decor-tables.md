# ADR-0014: Decor tables — visual attributes out of entity tables

## Status

Accepted (2026-09-12)

## Context

`types` carries `plural_name`, `icon`, `color`; `traits` carries `color`.
These are purely decorative: they paint sidebar rows, chips, tab icons and
trait dots, but never participate in validation, storage of values, or
identity. Mixing them into the entity tables conflates schema with
presentation, and every new decorated entity (ADR-0013 traits was the
second) re-answers the same "where do color/icon live" question ad hoc.

## Decision

Decor moves into its own table group `tables/decor/`, one table per
decorated entity:

- `type_decor(uuid PK FK→types.uuid ON DELETE CASCADE, plural_name TEXT
  NOT NULL, icon TEXT NOT NULL DEFAULT 'inventory_2', color TEXT NOT NULL
  DEFAULT '#9e9e9e')`
- `trait_decor(uuid PK FK→traits.uuid ON DELETE CASCADE, color TEXT NOT
  NULL)`

Decor is 1:1 with its owner and mandatory — every entity row has exactly
one decor row, created in the same `create()` call. Defaults live on the
decor columns (server_default), mirroring what `types.icon`/`types.color`
had before.

The columns are dropped from `types` and `traits`. The wire shape
(`TypeView`, `TraitView` in `contracts.ts`) is **unchanged** — `wire()`
joins decor in, so the frontend and all four gates see no contract diff.

## Migration

`_migrate_schema()` (server boot, idempotent):

1. `create_all` creates the decor tables on fresh DBs.
2. Backfill: `INSERT INTO type_decor (uuid, plural_name, icon, color)
   SELECT uuid, plural_name, icon, color FROM types ON CONFLICT DO NOTHING`
   (same shape for `trait_decor` from `traits`).
3. `ALTER TABLE types DROP COLUMN IF EXISTS plural_name, DROP COLUMN IF
   EXISTS icon, DROP COLUMN IF EXISTS color`; same for `traits.color`.

Prod (like every DDL): the migration runs at server boot, so deploy order
stays "push → CI → unit restart migrates in place". No manual psql needed.

## Consequences

- `Type` / `Trait` domain objects expose `plural_name`/`icon`/`color` as
  before, reading through the decor row; writers (`rename_type`,
  `create_enum`, `create_unit`, `sync_trait`, …) write decor rows.
- `views.py` tag-chip projection joins `type_decor` for the owner color
  instead of reading `types.color`.
- Deleting a type/trait cascades its decor row (FK ON DELETE CASCADE);
  no orphan sweep needed.
- New decorated entities copy the pattern: entity table + `*_decor` row in
  one create.
- `WType.ensure` keeps deriving `"<name>s"` for the plural when the caller
  passes none — the derivation now targets the decor row.
