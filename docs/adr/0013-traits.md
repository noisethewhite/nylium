# ADR-0013: Traits — reusable prop bundles attachable to types

- Status: proposed (2026-09-12)
- Date: 2026-09-12
- Builds on: ADR-0004 (embedded), ADR-0011/0012 (Row/Table), the
  name-grammar wire (`Array<T>`, `Numeric<Unit>`, `Function<T,R>`).

## Context

Types repeat the same prop clusters: every dated thing re-declares
`date`, every priced thing re-declares `price`, every owned thing
re-declares `owner`. Copies drift — fix the cluster once, the copies
stay stale. There is also no way to say "this prop holds a reference to
*anything that has dates*" — a prop's value type is always one concrete
type.

Max's call: Rust-style traits. A trait is a named, colored bundle of
prop definitions. Attaching a trait to a type gives the type those
props. In the object editor the fields that came from a trait are
tinted with that trait's color. A prop's value type can be either one
concrete type or "any type with trait X".

## Decision

### 1. Two new tables, two extended columns

```sql
CREATE TABLE IF NOT EXISTS traits (
    uuid  UUID PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS type_traits (
    type_uuid  UUID NOT NULL REFERENCES types(uuid)  ON DELETE CASCADE,
    trait_uuid UUID NOT NULL REFERENCES traits(uuid) ON DELETE CASCADE,
    -- attach order; trait prop groups render after the type's own props,
    -- in this order
    position   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (type_uuid, trait_uuid)
);

ALTER TABLE props
    ALTER COLUMN owner_type_uuid DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS owner_trait_uuid UUID
        REFERENCES traits(uuid) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS value_trait_uuid UUID
        REFERENCES traits(uuid) ON DELETE RESTRICT,
    ALTER COLUMN value_type_uuid DROP NOT NULL,
    ADD CONSTRAINT props_owner_exactly_one
        CHECK ((owner_type_uuid IS NULL) <> (owner_trait_uuid IS NULL)),
    ADD CONSTRAINT props_value_exactly_one
        CHECK ((value_type_uuid IS NULL) <> (value_trait_uuid IS NULL));
```

`props` gains a second unique constraint `(owner_trait_uuid, key)` next
to the existing `(owner_type_uuid, key)` — NULL keys are distinct in
Postgres, so each constraint guards exactly its own ownership kind.

Ownership is exclusive: a prop belongs to **one** type **or** **one**
trait. Value typing is exclusive: **one** concrete type **or** **one**
trait bound. `ON DELETE RESTRICT` on `value_trait_uuid` — a trait still
used as a prop's bound can't be deleted silently; the API refuses and
names the dependents (same policy as type deletes, `Api.delete_type`).

### 2. Effective schema = own props + attached traits' props

`Type.props` (and `WProp.all_for` consumers that render a schema) become
*effective*: the type's own props by `position`, then each attached
trait's props by `type_traits.position` then `props.position`. Key
collisions between a trait's props and the type's own (or another
attached trait's) props are rejected at attach time with a
`ValidationError` naming the key.

Values need no schema change: value tables are keyed by
`(inst_uuid, prop_uuid)` and don't care who owns the prop.

### 3. Wire grammar: `Any<TraitName>`

A trait-bound prop crosses the wire with
`value_type: "Any<TraitName>"`, joining the existing parameterized
grammar (`TypeNames.isTraitBound` / `anyParamOf` on the frontend, a
parser next to `_ensure_value_type` on the backend). Concrete props keep
plain names. `PropView` gains `trait: str | None` (origin trait name)
and `trait_color: str | None` — null for the type's own props. The
object editor tints a field's row when its `PropView.trait` is set.

Trait bounds accept **object references only** (instance_values) —
scalars, enums, units, arrays and embedded types can't carry traits, so
`Any<...>` as an array element or unit parameter is rejected in v1.

### 4. Trait props are plain stored props

No formulas (a formula references the *owner's* `Array<T>` props, and a
trait has many owners) and no function binding (same reason) in v1.
`formula` / `function_uuid` stay NULL on trait-owned props; the API
rejects attempts to set them there.

### 5. Detach and delete semantics

- **Detach trait from type**: instances of the type lose those fields;
  the API purges `(inst, prop)` value rows for the trait's props across
  the type's instances (same purge helper as retype, `WProp._purge_values`,
  extended per-instance-set). The prop rows themselves stay — the trait
  still owns them.
- **Delete trait**: refused while any type still has it attached or any
  prop anywhere is bound to it (`value_trait_uuid`). The error names the
  dependents.
- **Rename trait**: propagates freely — wire grammar resolves by name at
  the API boundary, storage is by uuid.
- **Retype of a trait prop / edit of a trait's schema**: one
  `sync_schema`-style draft against the trait as owner; retype purges
  values exactly like type-owned props.

### 6. API surface

```
list_traits() -> list[TraitView]
create_trait(name, color, props: dict[str, str]) -> TraitView
sync_trait(name, color, props draft) -> TraitView   # rename + recolor + schema
delete_trait(name) -> bool
attach_trait(type_name, trait_name) -> Type
detach_trait(type_name, trait_name) -> Type
```

`TypeView` gains `traits: list[TraitRefView]` (`{name, color}`) so the
type editor can render attach state and the sidebar can badge. Trait
bounds are set through the existing `create_type` / `sync_props`
`dict[str, str]` surface — `"Any<TraitName>"` as the value string.

### 7. Frontend

- Sidebar: a **Traits** section under Types — same row renderer pattern,
  color dot from `trait.color`.
- Trait editor page: name, color picker, prop list (reuses the type
  editor's prop rows minus the fixed `name` prop and minus
  formula/function affordances).
- Type editor: an **attach trait** row — a picker listing all traits;
  attached traits render as colored chips with a detach action; the
  trait's props render read-only in the schema list, tinted.
- Type-select (prop value type picker): a submenu "Any with trait…"
  listing traits; choosing one yields `Any<Name>`.
- Object editor: a field whose `PropView.trait` is set gets a left-edge
  tint / label color of `trait_color`; own fields render as today.

### 8. What traits are NOT

- Not inheritance: attaching a trait copies no uuid identity, adds no
  "is-a" queryable edge beyond `type_traits`, and instances remain
  instances of exactly one type.
- Not mixins with state: trait props are stored per instance exactly
  like own props; the trait holds only the schema.

## Consequences

- The schema read path (`Type.props`, `WProp.all_for`) must become
  trait-aware everywhere a *schema* is meant — but **not** in
  `sync_schema`'s write path, which edits only own props. The split is
  explicit: `own_props` (writes) vs `props` (effective, reads).
- `Any<...>` adds a fourth parameterized form to the name grammar; every
  grammar consumer (`TypeNames`, `_ensure_value_type`,
  `_normalize_value`, ref validation) learns it. Ref validation for a
  trait-bound prop checks the target instance's type against
  `type_traits`.
- Two existing NOT NULLs relax — prod migration is additive and
  idempotent through the usual `migrate()` path.
