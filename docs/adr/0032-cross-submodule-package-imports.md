# ADR-0032: Cross-submodule imports go through the package, not the file

- Status: superseded by ADR-0033 for the SQL persistence layer
- Date: 2026-09-20

## Context

`nylium` is a package of submodules by concern (`objects/`, `tables/`,
`rows/`, `api/`, `auth/`, `server/`, …), and each submodule is itself a
package whose `__init__.py` re-exports its public symbols. During the
ADR-0031 split (`tables` / `rows`) it became clear that there was no
consistent rule for *how* one submodule imports from another: some sites
did `from nylium.tables.objects import Prop`, others reached into a leaf file
(`from nylium.tables.objects.props import Prop`). The latter couples the
importer to the file layout, so a file rename, a moved class, or a split of
one module into several breaks callers that never cared which file held the
symbol.

Max wants one rule: **a cross-submodule import must name the submodule, not
the file.**

## Decision

1. **Cross-submodule imports are package-level.** When module A (in submodule
   X) imports a symbol that lives in submodule Y, it imports from `nylium.Y`,
   i.e. `from nylium.tables.objects import Prop`, never
   `from nylium.tables.objects.props import Prop`. The public surface of each
   submodule is its `__init__.py`; a leaf file is an implementation detail.
2. **Every submodule's `__init__.py` is the single re-export point** for the
   symbols other submodules may consume. Leaf modules do not need to be
   importable by path from outside their own submodule.
3. **Intra-submodule imports stay file-level.** Within one submodule, modules
   may import from sibling files directly (`rows/decor/__init__` importing
   `rows.decor.type_decor`). The rule governs *cross*-submodule edges only.
4. **Leaf modules are not submodules.** A mapped-dataclass file such as
   `tables/values/string_values.py` (`TABLE_StringValues`) is a leaf with no
   `__init__` of its own; importing it is not a "cross-submodule" edge. Row
   classes therefore bind `__table__` directly to the leaf mapped class
   (`from nylium.tables.values.string_values import TABLE_StringValues`) — see
   the exception below.

## Exceptions

- **`Row → TABLE_*` stays leaf-level.** A Row class binds `__table__` to its
  mapped dataclass. Importing it package-level (`from nylium.tables.values
  import TABLE_StringValues`) drags in the whole `values/__init__`, which
  re-exports the Table stores, which import the Row class back — a
  `tables ↔ rows` cycle. The leaf mapped-dataclass file is a value object with
  no back-edges, so `from nylium.tables.values.string_values import
  TABLE_StringValues` is the one sanctioned leaf import, and it is not a
  "cross-submodule" edge under Decision #4.
- **Bidirectional Row navigation** (`Type.props ↔ Prop.value_type`,
  `Type.traits ↔ Trait.attached`) is inherently cyclic. These back-edges are
  lazy function-level imports (not module-level), and the Row modules carry
  `# pyright: reportImportCycles=false` with a comment explaining why the
  static cycle is benign (no runtime cycle).

## Consequences / risks

- **Import order is load-bearing** (already true per ADR-0012): each
  `__init__.py` imports `TABLE_*` leaves before the Table stores, and the
  "heavy" Row modules (`type.py`, `trait.py`, `instance.py`) are imported
  last inside `rows/objects/__init__` so their store-touching navigation is
  available only after the stores exist.
- **A leaf-constants module was introduced** (`objects/scalar_type_names.py`)
  to break a `tables → objects → tables` cycle over scalar `TYPE_NAME`
  strings; both layers import only the leaf.
- **Static cycles remain flagged.** The `Row → TABLE_*` leaf exception plus
  lazy navigation keeps the runtime acyclic, but pyright still reports the
  `rows.objects ↔ tables.objects` static cycle; the relevant modules carry the
  `reportImportCycles=false` pragma. This is a documented, reviewed exception,
  not a silent disable.
- **If the leaf exception is ever unacceptable**, the clean resolution is a
  dedicated leaf layer `tables/schema/` holding all 30 `TABLE_*` mapped
  classes. Then the graph becomes a strict DAG — `schema ← rows ← tables ←
  consumers` — and every cross-submodule import, including `Row → TABLE_*`,
  can be package-level with no cycle and no pragma. That is a follow-up ADR,
  not part of this one.

## Migration

- **Step 1** — convert consumer-layer imports (`objects/`, `api/`, `auth/`,
  `server/`) from `nylium.tables.<file>` / `nylium.rows.<file>` to package
  form.
- **Step 2** — convert `store → Row` imports to package form
  (`from nylium.rows.objects import Prop`).
- **Step 3** — convert the root `tables/__init__.py` to import from its
  submodules' packages rather than their leaf files.
- **Step 4** — reorder `__init__.py` files (`TABLE_*` before stores; heavy Row
  modules last), add the `scalar_type_names` leaf, and apply the
  `reportImportCycles=false` pragma where bidirectional navigation is by
  design.

Gates: `uv run basedpyright` → 0/0/0, `uv run ruff check src` → clean,
`uv run pytest` → 295 passed.
