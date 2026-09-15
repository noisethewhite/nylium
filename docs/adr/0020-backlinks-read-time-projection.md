# ADR-0020: Backlinks as a read-time projection

## Status

Accepted — 2026-09-15

## Context

Objects link forward only: a link prop is a row in `instance_values`
(target uuid as pk), array membership is a row in `array_values`. ADR-0005
already reverse-projects *array membership* onto the member as derived
tags, but nothing surfaces the general reverse question — "which objects
point at this one?" — for direct link props. Knowledge-base usage
(second brain, ADR-0009) needs exactly that view.

## Decision

`ObjectView.backlinks: list[ObjectRef]` — every owner instance that
points at the object, gathered from both edge stores:

1. direct links: `instance_values WHERE uuid = :target` → owner instance;
2. array membership: `array_values WHERE value_uuid = :target` → array
   box → its owner's link row in `instance_values` → owner instance.

Owners are deduplicated (an owner linking both directly and via an array
appears once) and returned in deterministic `(type_name, uuid)` order.

**Nothing is stored.** The backlink set is recomputed on every read —
two indexed queries, no N+1 — mirroring the ADR-0005 tag projection.
Backlinks can therefore never drift out of sync with the forward edges;
renames, retypings and deletions need no backlink maintenance.

The SQL statement lives in `tables/values/backlinks.py` (ADR-0019); the
api layer only maps rows to `ObjectRef`. Tags (ADR-0005) keep their
richer payload (owner display name, prop key, color) and stay the
array-specific view; backlinks are the type-level "who references me".

## Consequences

- One extra query per direction on every object read — same cost class
  as the existing tag projection.
- Direct links are storage-level 1-per-target: `instance_values` is
  keyed by the target uuid, so at most one direct-link backlink exists
  per object. Many→one references go through arrays (array_values is
  unkeyed by member), and those project any number of backlinks.
- No schema change, no migration, no write-path work.
- Frontend contract `ObjectView` gains `backlinks: ObjectRef[]`.

## Alternatives considered

- *Materialized backlink table* — rejected: introduces drift risk and
  write-path maintenance for zero read savings at this scale; violates
  the ADR-0005 precedent that reverse views are projections.
- *Reuse the tag projection for direct links* — rejected: tags carry
  prop-level naming and color semantics that don't fit plain references;
  conflating the two would blur both views.
