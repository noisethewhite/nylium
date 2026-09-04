# ADR-0004: Embedded instances (composition)

Status: proposed
Date: 2026-09-04

## Context

Some types only make sense as a part of another object, never
standalone: `ContactDetails` of a `Person`, `Address` of a `Company`.
Today the only way to model that is a ref prop pointing at a regular
object — which forces the user to create a separate named object
("Vasya's Contact Details") and edit it in a separate tab, torn away
from the parent it belongs to.

The user wants **embedded instances**: objects whose sole purpose is
being a prop value of a parent object, edited inline in the parent's
editor, with names generated automatically.

This is UML composition: the child's lifecycle is owned by the parent.

## Decisions

### Type-level flag

1. **Embeddedness is a property of the type, not the prop** — a new
   nullable-free column `types.embedded Boolean NOT NULL DEFAULT
   FALSE` (ALTER in `App._ensure_schema`, same idempotent pattern as
   `numeric_values.unit`). An embedded type cannot be instantiated
   standalone: `POST /objects/{type}` with an embedded type → 422.

2. Embedded types are otherwise normal types: own props, icon, color,
   rename/delete through the existing paths (delete-in-use guard
   unchanged). They are NOT a new `types.kind` — embeddedness is
   orthogonal to kind (`type`/`enum`/`unit`).

3. The type-create form gets an "Embedded" checkbox; the type panel
   shows the flag. Embedded types stay visible in the sidebar's type
   list (schemas are editable), objects of embedded types do not
   appear in object lists.

### Ownership (exclusive, derived from the refs graph)

4. The ownership edge IS the ref: a prop whose `value_type` is an
   embedded type holds a normal RefValue pointing at the child. **The
   child has exactly one owner** — no other prop may reference an
   embedded object. Enforced in the API layer: any write path that
   would point a second ref at an embedded object, or point a ref at
   an embedded object from a prop whose value_type is not that
   embedded type, → 422.

5. For fast filtering and name regeneration the ownership is
   denormalized onto the object row: `objects.owner_object_uuid UUID
   NULL` + `objects.owner_prop_uuid UUID NULL` (ALTER in
   `_ensure_schema`). NULL on regular objects. The refs table stays
   the source of truth; the columns are a read-side index.

### Generated names

6. Every object still has a `name` — the invariant is untouched. An
   embedded object's name is **generated, not user-entered**:
   `<parent name> → <prop key>`, e.g. `Vasya → Contact Details`.
   Nested embedded: `Vasya → Contact Details → Address`.

7. **`→` (U+2192) becomes a reserved character**: it is rejected in
   user-entered object names and type names (422). This makes the
   generated name unambiguous — everything after the first `→` is the
   prop path, everything before is a real object name.

8. The generated name is stored as the ordinary name-prop value, so
   search, lists and labels work with zero special cases. It is
   **regenerated** when the parent's name or the prop's key changes
   (recursive walk over embedded children). The name field of an
   embedded object is read-only in the UI.

### Cascade lifecycle

9. Deleting the parent object **cascade-deletes** its embedded
   children (recursive over the refs graph where the target is
   embedded). Clearing an embedded prop (setting it to null) deletes
   the child. Deleting an embedded object directly is allowed only
   through the parent's prop write — the standalone delete endpoint
   refuses embedded objects (422), so ownership can't dangle.

10. Creation is lazy: an embedded prop starts as null; the child is
    created when the user first enters data in the inline section (or
    presses its "+" button), inside the parent's save transaction.

### Editing UX

11. In the object editor an embedded prop renders as a collapsible
    **inline section** — the child's props rendered with the same
    FieldFactory machinery, indented under the parent prop, no tab
    switch. Ctrl+S on the parent saves the whole tree in one
    transaction (parent + all touched embedded descendants).

12. The ref-picker for an embedded-typed prop is **replaced** by the
    inline section — there is no "pick an existing object" for a type
    that cannot exist standalone.

### Visibility rules

13. Embedded objects are excluded from:
    - sidebar object lists,
    - NameSearch/ref pickers (they cannot be referenced from outside),
    - global name search in phase 1 (can be revisited — showing them
      with a `Parent → …` path label is a pure UI change later).

### Out of scope (phase 2 candidates)

- `Array<EmbeddedType>` — arrays of embedded children. Natural
  continuation, but adds per-item add/remove/reorder UI to the inline
  section. Deferred.
- Moving an embedded child to another parent (re-parenting). Deferred.
- Showing embedded objects in global search with path labels.

## Consequences

- The refs graph gains a second semantic role (ownership) next to
  plain references; every ref write path must now know whether the
  target type is embedded.
- Name regeneration on rename is O(embedded subtree) — fine at nylium
  scale, and capped by the exclusive-ownership invariant (a tree, not
  a DAG).
- The `→` reservation is a small breaking constraint on user input;
  existing names containing `→` are grandfathered (validation happens
  on write, not retroactively).
