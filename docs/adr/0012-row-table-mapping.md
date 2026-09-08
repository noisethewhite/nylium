# ADR-0012: Row/Table — SQLAlchemy lives only inside table abstractions

- Status: accepted (2026-09-08)
- Date: 2026-09-08
- Supersedes: ADR-0011 entirely (`tableproperty`, `TableDomain`, the
  descriptor-based auto-persist). Keeps ADR-0010's Row layer and `TABLE_`
  naming.

## Context

ADR-0011 introduced a custom descriptor (`tableproperty`) plus a generic
`TableDomain` base so that a domain object could be annotated once and get
column access, reverse lookup (`foreach`) and write-through persistence
"for free". In practice:

- The descriptor was a bespoke typing construct that LSPs and basedpyright
  could not model honestly (`tableproperty[Owner, T]` lying about what
  attribute access returns), which already caused a CI failure when PEP 649
  deferred annotations met Python 3.12 eager evaluation.
- Lookups and mutations were smeared across per-table private helpers
  (`by_hash`, `for_user`, `mark_used`, `update`, `rename`, `sync`, ...),
  each with its own name and return shape.
- `foreach` returned different things in different modules, and several
  one-caller functions existed only to wrap a two-line SQL snippet.

Max's call: all SQLAlchemy stays inside the table abstraction classes. A
table behaves as `Mapping[pk, Row]`; a `Row` is a dataclass-flavoured
snapshot whose assignment writes through to SQL. No Views at the storage
layer. Uniform method names, generators over lists, narrow helpers and
single-purpose factories deleted (folded into constructors).

## Decision

### 1. `tableproperty` and `TableDomain` are deleted

`basic/tableproperty.py` and `database/tabledomain.py` are gone from the
tree. Nothing replaces them one-for-one.

### 2. `database/table.py` is the whole SQL seam

Two generic bases:

- **`Row`** — one mapped row as a plain object. `Row.__init__` copies every
  mapped column into instance attributes (`sqla.inspect` on the mapped
  class). Attribute and item access read the snapshot. `row.field = value`
  or `row["field"] = value` writes through: an `UPDATE … SET field WHERE
  pk`, committed through the existing `@databasemethod(commit=True)`
  semantics (nested writes inside an outer databasemethod share its session
  and commit once at the boundary). The primary key is identity: copied at
  construction, never written through.
- **`Table[K, R]`** — `collections.abc.Mapping` over one mapped class:
  - `table[key]` → SELECT by PK, construct the `Row`, raise `KeyError`.
  - `table.where(**eq)` → the *single* reverse lookup every table answers:
    a generator of `Row`s whose columns equal the given values.
  - `table.all()` → `where()` with no criteria.
  - `iter(table)` → PKs; `len(table)` → `COUNT(*)`; `key in table` comes
    free from `Mapping`.

Generators materialise inside one `SessionContext` and yield after it
closes, so abandoning iteration early never strands a connection.

### 3. Uniform idioms replace per-table helpers

| old helper                     | new idiom                                  |
| ------------------------------ | ------------------------------------------ |
| `X.field.foreach(v)`           | `table.where(field=v)` (generator)         |
| `by_hash(h)` / `by_name(n)` …  | `next(table.where(field=v), None)`         |
| `mark_used` / `update` / `rename` | `row = table[key]; row.field = value`   |
| `register(...)` / factories    | `table.create(...)`                        |
| `count_all()`                  | `len(table)`                               |
| `for_user(uuid)`               | `table.where(user_uuid=uuid)`              |

Concrete tables (`types`, `props`, `enum_options`, `unit_parts`, `files`,
`api_tokens`, `auth_users`, `auth_credentials`, `auth_challenges`,
`auth_sessions`, `instances`) add only real business operations —
`create`, `sync`, `delete` — nothing that restates the Mapping protocol.

### 4. Typing posture

`Row` subclasses annotate their columns but initialise none of them; the
base constructor assigns dynamically. Each row module carries a file-level
`# pyright: reportUninitializedInstanceVariable=false` saying exactly that.

Row navigation is bidirectional by design (`Type.props` ↔
`Prop.value_type`); the back-edges are lazy function-level imports, so
there is no runtime cycle — `reportImportCycles` is disabled per file with
a comment explaining why. This is the deliberate trade: navigation stays
on the rows (used by `wire()` and the codec), and the type checker is told
about the one place it cannot see through.

## Consequences

- Call sites lose the bespoke vocabulary; the same six idioms appear
  everywhere, which is the point — a new table needs no new helper API.
- `where(**eq)` matches by column name strings; basedpyright checks the
  `Row` annotations but not the `filter_by` kwargs. Accepted: the uniform
  surface is worth more than per-column overloads.
- `Row` snapshots go stale if another writer touches the same row
  concurrently. Single-user personal app; acceptable.
- Wire/serialisation shape (`web/src/contracts.ts`) is unchanged — `wire()`
  methods stayed on the rows and produce the same dicts.
