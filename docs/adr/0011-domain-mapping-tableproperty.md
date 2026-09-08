# ADR-0011: Domain tables as mutable Mappings with auto-persist (`tableproperty`)

- Status: superseded by ADR-0012 (2026-09-08)
- Date: 2026-09-07
- Supersedes: the Store layer of ADR-0010 (sections 2 and the per-entity
  stores of section 5). The Row layer and the `TABLE_` naming of ADR-0010
  stay; the *Domain* intent of ADR-0010 is kept but re-expressed.

## Context

ADR-0010 split the fused table classes into Row + Store. The Store pilot
(`Types`, then `Instances`/`Props`/`Files`/`EnumOptions`/`UnitParts`)
exposed the flaw in that split: a Store is a *third* representation of the
same entity. The parts of a unit now live as `TABLE_UnitParts` (row),
`UnitParts` (store of rows) and `UnitPartView` (display DTO) — three shapes
of one thing, and none of them is writable as an object. Reading is
dict-like (`unit_parts[uuid]`), but writing still means reaching for the
raw row (`part.name = x` on a mapped class), and the domain meaning of a
unit part (its affine conversion, its rename propagation) has no home that
isn't either an anemic row or a frozen view.

Max's call: drop the Store. A table's abstraction should be a
`Mapping[UUID, DomainObject]` where the domain object *is* the writable
thing — mutating it writes through to the table. The `*View` DTOs are a
fourth representation on top; they fold into the domain objects.

## Decision

### 1. The Store base class dies; a table's abstraction is a Mapping of domain objects

`database/store.py` is removed. Each domain table gets:

- `TABLE_Xxx` — the thin row (unchanged, `TABLE_` naming from ADR-0010).
- `Xxx` — the **domain object**: holds a snapshot of one row's data, is
  writable, and writes through to the row on mutation (§2).
- `Xxxs` — the **table abstraction**: `Mapping[UUID, Xxx]` directly (no
  generic base), exposed as a singleton `xxxs`. `xxxs[uuid] → Xxx`,
  `uuid in xxxs`, `for uuid in xxxs`, `len(xxxs)`.

A `Mapping` yields *domain objects*, not rows — callers never see
`TABLE_Xxx` outside the table module and genuine SQL joins.

### 2. Domain fields are `tableproperty[T]` — write-through on assignment

A domain field is a `tableproperty`, not a plain attribute or a read-only
`property`:

```python
class UnitPart:
    _table = TABLE_UnitParts
    uuid: UUID                       # identity, read-only
    name: tableproperty[str]
    multiplier: tableproperty[Decimal]
    offset: tableproperty[Decimal]
    is_base: tableproperty[bool]
    position: tableproperty[int]
```

- **Read** (`part.name`) returns the instance's snapshot value.
- **Write** (`part.name = "kg"`) sets the snapshot *and* issues
  `UPDATE … SET name = 'kg' WHERE uuid = part.uuid` inside a
  `@databasemethod(commit=True)` — so the owner-commits-once semantics
  (ADR on transaction atomicity) are preserved: nested writes share the
  outer session and commit once at the boundary.
- **Class access** (`UnitPart.name`) returns the column accessor, exposing
  `list_for` (§3).

The `uuid` is identity, not a `tableproperty`: it is set at creation and
never written through.

### 3. `tableproperty.list_for(value)` — reverse lookup on the column

Accessed on the class, a `tableproperty` answers "every domain object whose
column equals this value", lazily:

```python
UnitPart.name.list_for("kg")        # Generator[UnitPart] where name == 'kg'
```

This is the per-column index that ADR-0010 had to bolt onto the Store as
`by_name`. On a `tableproperty` it needs no extra method — the column *is*
the index.

### 4. Query helpers return `Generator`, not `list`

`Xxxs.list_for(...)` and the other "give me the rows where …" helpers yield
domain objects lazily (`Generator[Xxx, None, None]`) instead of building a
list. The generator owns its `SessionContext` for the duration of the
iteration and releases it on exhaustion or `close()`, so laziness does not
leak sessions. Callers that need a list say `list(...)` explicitly.

### 5. The `*View` DTOs fold into the domain objects; `api/views.py` is removed

`UnitPartView`/`TypeView`/`PropView`/`EnumOptionView`/… were frozen copies
of the same data for the API boundary. With a writable domain object there
is one representation: the API serializes the domain object itself. The
serialization shape the frontend already consumes is kept — the domain
object carries the same fields the view carried. `api/views.py` shrinks to
the genuinely API-shaped aggregates (the `PropValue` union,
`ObjectRef`/embedded drafts) that have no single-table home.

### 6. Scope: every table, including auth

This is the shape for **all** table abstractions, auth included
(`auth_users`, `credentials`, `sessions`, `challenges`, `api_tokens`).
The WebAuthn ceremony (`issue`/`consume`/`verify`/`purge`) is not table
access and stays a service over the auth mappings — it does not become a
`tableproperty` concern.

## Consequences

- **Two representations, not four.** Row (SQL) and domain object
  (everything else). The Store and the View both disappear.
- **Writing is as native as reading.** `part.multiplier = Decimal("1.8")`
  persists; no `store.update(uuid, ...)` round-trip, no raw-row reach.
- **The Mapping key type stays honest.** One key (UUID) on `Xxxs`;
  secondary indexes are `Xxx.column.list_for(value)`, not overloaded
  `__getitem__`.
- **Auto-persist is per-field.** Each assignment is an `UPDATE`. Editing
  several fields of one object issues several statements inside the shared
  transaction — acceptable at nylium's scale, and the single-commit
  boundary still holds. A batched `flush()` is a possible later refinement
  if a hot path ever needs it.
- **`list_for` laziness has a session contract.** A half-consumed
  generator holds its session; callers that abandon iteration should
  `close()` it or consume fully. The common `for … in` and `list(…)`
  patterns are safe.
- **Big-bang risk is contained by phasing** (below); no half-migrated
  state is committed.

## Rollout

1. `tableproperty` descriptor + the `UnitPart`/`UnitParts` pilot (the
   clearest domain object), migrating its call sites off
   `unit_parts.<helper>` onto the Mapping and `tableproperty.list_for`.
2. The remaining domain tables (`Instances`, `Props`, `Files`,
   `EnumOptions`, `Types`, value tables) in separate diffs.
3. The auth tables.
4. Fold the `*View`s into domain objects; shrink `api/views.py`; the API
   serializes domain objects.

## Rejected

- **Keep the Store, add write-through to it.** That keeps three
  representations and pushes the domain object one more hop away; the
  Store buys nothing a `Mapping` of domain objects doesn't already give.
- **SQLAlchemy mapped classes as the domain objects** (write `part.name`
  straight on `TABLE_UnitParts`). That re-fuses the row and domain roles
  ADR-0010 separated, and puts ORM unit-of-work magic (dirty tracking,
  implicit flush) back in charge of persistence — the opposite of the
  explicit write-through wanted here.
- **Batched `flush()` instead of per-field write.** Defers the failure
  point away from the mutating line and complicates the transaction story;
  per-field write-through keeps the effect of `part.name = x` local and
  obvious. Revisit only on a measured hot path.
- **`list` from query helpers.** Materializes the whole table on every
  call; a `Generator` with an owned session is the lazy form the data
  volume will eventually need.

## LOC estimate

`tableproperty` + pilot ~150–200; per-table rollout ~100–150 each across
~8 tables; auth ~150; view-folding + API serialization ~200–300. Far over
the 250-LOC bar — ships in the phased diffs above.
