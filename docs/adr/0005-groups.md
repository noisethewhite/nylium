# ADR-0005: Groups (tag-based membership + aggregate props)

Status: proposed
Date: 2026-09-04

## Context

Objects often form collections that are *derived*, not curated: all
`Product`s of one receipt, all `Task`s of a project. Today the only
way to model that is a manual `Array<Ref>` prop — the user adds every
member by hand and the list goes stale the moment a new matching
object appears.

The user wants **groups**: a group is an instance of a group type
(e.g. `Receipt<Product>`), membership is assigned on the *member*
side as a **tag**, and every object carrying the group's tag is
automatically a member — no manual list maintenance. On top of that,
group types get **computed props**: aggregations over a prop of the
members (a `Receipt<Product>` whose `Total` is the sum of its
members' `Price`).

This supersedes the standalone "computed props" idea: computation is
introduced scoped to group aggregates, not as a general formula
system.

## Decisions

### Group types

1. **Groupness is a property of the type, bound to one member type**
   — a new column `types.group_of TEXT NULL` (ALTER in
   `App._ensure_schema`). NULL = not a group. When set, it names the
   member type: `Receipt.group_of = "Product"`. The member type is
   fixed at group-type creation, same as `embedded`.

2. Groupness is orthogonal to `types.kind` and mutually exclusive
   with `embedded` (a type is plain, embedded, or a group — the
   type-create form radio-selects at most one flag). Group objects
   are **standalone**: they appear in lists, search and pickers like
   any normal object.

3. A group type's schema starts with two pinned props:
   - `name` (the universal pinned prop, user-entered as usual),
   - `members` — pinned, `value_type = Array<group_of>`, **system
     managed**. It is a real prop row (the schema shows it, second
     after `name`), but its value is never stored: it is derived at
     read time from the tag edges (see below). Any write to
     `props["members"]` → 422. `members` is a reserved prop key on
     group types.

4. The member type must be a non-embedded object type; `group_of`
   pointing at an embedded/enum/unit type → 422. Deleting a type that
   is some group type's `group_of` → 422 (existing delete-in-use
   guard, extended).

### Tags (membership edges)

5. Membership lives on the member side as a **tag**: an edge from the
   object to the group instance. New table (created in
   `_ensure_schema`):

   ```
   group_tags(object_uuid UUID FK instances CASCADE,
              group_uuid  UUID FK instances CASCADE,
              PRIMARY KEY (object_uuid, group_uuid))
   ```

   One object may carry **many tags** — a `Product` belongs to any
   number of receipts. Deleting either end cascades: delete a group
   and its members simply lose the tag; delete a member and the
   group's member list shrinks. Nothing dangles.

6. The tag is the ONLY way in or out of a group — there is no manual
   "add member" on the group side. A group's `members` value is
   `SELECT object_uuid FROM group_tags WHERE group_uuid = :g`, wrapped
   as the usual `ArrayValue` of refs at read time.

7. Tag validity is enforced on write: the tag target must be an
   object of a group type whose `group_of` equals the tagging
   object's type. `Product` → tag of `Receipt #3` ✓; `Product` → tag
   of `Project X` (group_of = Task) → 422. Tags on embedded objects
   are rejected (422) — embedded children are not standalone and
   cannot be group members.

8. Wire/API: `ObjectView` gains `tags: list[ObjectRef]` (the group
   instances this object is tagged with). `update_object` accepts an
   optional `tags` field — full replacement of the tag set, validated
   per (7), saved in the same transaction as props. The object editor
   shows a **Groups** chip section (same chip UX as enum arrays) with
   an add-picker over groups whose `group_of` matches the object's
   type; Ctrl+S saves props + tags together.

### Computed (aggregate) props

9. Beyond the pinned props, a group type's props are ordinary —
   **except each may be declared computed**. Two nullable columns on
   `props`: `aggregation TEXT NULL` (`sum` | `avg` | `min` | `max` |
   `count`) and `aggregation_path TEXT NULL` (the member prop key to
   aggregate; NULL for `count`).

10. Computed props are **evaluated at read time**, never stored: on
    fetch of a group object, each computed prop is resolved over the
    current members' values for `aggregation_path`. Writes to a
    computed prop → 422. At nylium scale read-time evaluation is
    cheap; no invalidation machinery exists to get wrong.

11. Type rules: for `sum`/`avg`/`min`/`max` the path must name a
    numeric (`Integer`/`Decimal`) prop of the member type, and the
    computed prop's own `value_type` must be `Decimal` (`Integer`
    allowed for `count`, which always aggregates the member list
    itself). Violations → 422 at prop-create/update time.

12. Rename coupling: renaming a member prop key that is referenced as
    an `aggregation_path` rewrites the path (same transaction as the
    key rename). Deleting such a prop → 422 until the computed prop
    is removed or switched to manual.

13. In the group object's editor, computed props render **read-only**
    with a `Σ` marker; `members` renders as a read-only chip list of
    the derived members. In the type editor, a group type's prop rows
    gain an aggregation selector (manual / sum / avg / min / max /
    count + member-prop path picker).

### Visibility & UI

14. Group types show a `group` badge in the sidebar type list and the
    type panel (same slot as the `embedded` badge). Group objects are
    ordinary for lists/search/pickers — a group can itself be tagged
    into a group-of-groups, referenced by props, etc.

15. Type-create form: a **Group** checkbox with a member-type picker
    (object types only, embedded excluded), mutually exclusive with
    the Embedded checkbox.

## Out of scope (phase 2 candidates)

- General computed props outside groups (formulas, string templates,
  cross-ref paths like `members → address → city`). Deferred — the
  aggregation columns are deliberately narrow so a future expression
  system can replace them without a data migration of stored values
  (nothing is stored).
- Multi-hop aggregation paths (`sum:price.amount`).
- Aggregations over `Bool`/dates; `median`, `count_distinct`.
- Ordering/subgroups of members.

## Consequences

- The refs graph gains a third semantic role (membership) next to
  plain refs and embedded ownership; `group_tags` is a separate table
  precisely so ref-write paths stay untouched — tags are not props.
- Read-time derivation of `members` + computed props means a group
  fetch costs one tag scan plus one prop batch-read per member —
  linear in group size, fine at nylium scale, and always consistent
  by construction (no denormalized state to invalidate).
- Tag edges are invisible to `list_objects` and search: no visibility
  rules needed, unlike embedded.
- `Receipt<Product>`-style parametric display is a UI concern only;
  the type is just `Receipt` with `group_of = "Product"` — no
  generic-type machinery is introduced.
