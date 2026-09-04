# ADR-0005: Array-backed tags and formula props

Status: proposed (supersedes the group-type draft of 2026-09-04)
Date: 2026-09-04

## Context

The first draft of this ADR introduced dedicated *group types*
(`types.group_of`, a `group_tags` table, pinned `members` props).
The user revised the idea into something simpler and more general:

**No special group concept.** ANY prop of type `Array<T>` is a
collection that can be filled two ways — manually (search & pick on
the owner side) and via **tags** (on the member side). When an object
lands in such an array it automatically carries a tag named
`<Object Name> -> <Prop Name>`; assigning that tag to an object makes
it a member of the array. Other props of the owner may be **computed
by formulas over the array's members** (Excel-flavored: a
`Receipt`'s `Total` = `SUM(items.price)`).

Tags show directly under the object's name and have their own color.

## Decisions

### Tags are derived back-references of array membership

1. Every prop `p: Array<T>` on type `S`, where `T` is a standalone
   (non-embedded) object type, automatically defines, for every owner
   instance `o` of `S`, a **tag** identified by the pair `(o, p)`.
   No opt-in, **no new tables**: the edge set IS the array's stored
   refs; a tag is a read-side projection of one such edge onto the
   member object. Scalar arrays (`Array<String>` …) have no tags —
   there is no object to tag. `Array<Embedded>` stays forbidden
   (ADR-0004).

2. The tag's name is exactly `<o name> → <p key>` — one derived
   string, e.g. `Receipt #3 → items`. Renaming the owner object or
   the prop key renames the tag **by construction**: nothing is
   stored, nothing to rewrite, name and tag can never drift apart.
   The `→` glyph is already reserved in all user-entered names
   (ADR-0004), so no user name can collide with a tag name.

3. An object displays one chip per membership edge — sitting in
   three receipts' `items` shows three chips: `Receipt #1 → items`,
   `Receipt #3 → items`, `Receipt #7 → items`. No deduplication:
   each chip is one concrete edge to one concrete owner. Chips render
   **directly under the object's name** in the editor header.

4. Each tag has its own color, derived deterministically by hashing
   the tag name into the palette — stable across sessions, distinct
   across tags. Not user-configurable in v1.

### Two-way membership editing

5. Owner side (existing behavior, free): adding an object to the
   array via search appends the ref — the member instantly shows the
   tag, because the tag is derived. No extra write paths.

6. Member side: the object's tag section offers *add tag* → pick the
   owner instance `o` (search over objects whose type has an
   `Array<T>` prop matching the object's type) → pick the prop `p`
   (if `o`'s type has several matching array props) → the ref is
   appended to `o`'s array. The same edge, created from the other
   side; validation and storage are the ordinary array-write path.

7. Removing a tag chip removes **exactly that one edge** — the tag
   IS a concrete `(owner, prop)` pair, so there is nothing to
   disambiguate and no bulk side effects.

### Formula props

8. Any prop of `S` may be declared computed: a new nullable column
   `props.formula TEXT` (idempotent ALTER in `_ensure_schema`). A
   formula is an Excel-flavored expression over the owner's own array
   props: the functions `SUM`, `AVERAGE`, `COUNT`, `MIN`, `MAX`
   applied to a member path `<arrayKey>.<memberPropKey>`, combined
   with arithmetic (`+ - * /`, parentheses) and numeric literals.
   Example: `SUM(items.price) * 1.21`.

9. Computed props are **evaluated at read time, never stored**.
   Writing a computed prop → 422. Members whose value at the path is
   NULL are skipped (Excel ignores blanks). The computed prop's
   `value_type` must be `Decimal` (`Integer` allowed when the formula
   is a bare `COUNT(...)`); anything else → 422 at prop save.

10. Formulas are **parsed and type-checked when the prop is saved**:
    unknown function, unknown array key, non-array key, unknown or
    non-numeric member prop, syntax error → 422 with a precise
    message. Renaming a referenced key (array prop or member prop)
    rewrites the stored formula in the same transaction as the
    rename; deleting a referenced prop → 422 while any formula
    references it.

11. v1 formulas reference only the owner's own array props and
    literals — no prop-to-prop references, no cross-object paths, no
    conditionals. This keeps the parser a small recursive-descent
    over a fixed grammar and leaves room for a real expression
    engine later without stored-value migrations (nothing is stored).

12. UI: computed props render read-only in the object editor with a
    `Σ` marker; the type editor gains a formula input per prop with a
    function cheat-sheet (`SUM/AVERAGE/COUNT/MIN/MAX(array.prop)`).

### Visibility

13. Tags live under the object's name in the editor; they are not
    objects, not types, not props — no sidebar, picker, or search
    changes. Object fetch gains one reverse-ref query to project the
    tags.

## Out of scope (phase 2 candidates)

- User-chosen tag colors; per-owner chips; tag-based filtering /
  "all objects with tag X" views (a pure read-side addition later).
- Richer formulas: `IF`, string functions, prop-to-prop references,
  cross-object paths, formulas referencing other formulas.
- Tag-driven member ordering.

## Consequences

- Schema cost: **one column** (`props.formula`). Tags reuse the
  existing array-ref storage — membership and tags are the same rows
  and cannot desync by construction.
- Rename-safety is structural: tag names and formula references are
  either derived (tags) or transactionally rewritten (formulas).
- Read-time evaluation makes a group/object fetch linear in member
  count — fine at nylium scale, and always consistent (no
  denormalized state to invalidate).
- The earlier group-type draft is fully superseded: no `group_of`,
  no `group_tags` table, no pinned `members` prop — every array prop
  is already a group.
