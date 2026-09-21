# ADR-0033: Persistence layer is one class per file — tables in `tables`, rows in `rows`

- Status: proposed
- Date: 2026-09-21
- Supersedes: ADR-0032 for the SQL persistence layer (`tables` / `rows` / `table_rows`)

## Context

ADR-0031 split the persistence layer into `tables/` and `rows/`; ADR-0032 then
made package `__init__.py` files the import contract and, after the TABLE_*
removal, the implementation collapsed into `nylium/table_rows/` with
`tables/` and `rows/` left as re-export shims. That hid the real rule Max
wants: **a Table heir lives in `nylium/tables`, a Row heir lives in
`nylium/rows`, one class per file.** `table_rows/` is only the fallback for a
Table+Row pair that genuinely cannot be separated without a module-level
import cycle — and after moving the registry, there are no such pairs.

## Decision

1. **Row heirs live in `nylium/rows/`.** Every mapped dataclass (`Row`)
   is alone in its file; the file name is the snake_case class name.
2. **Table heirs live in `nylium/tables/`.** Every `Table[...]` store is
   alone in its file; the file name is the snake_case class name. A table
   module imports its Row module directly (`tables/objects/props.py` →
   `rows/objects/prop.py`).
3. **`nylium/database/registry.py` owns `reg`.** Rows decorate with
   `@reg.mapped_as_dataclass` without importing `nylium.tables`, so the
   `rows → tables` edge is gone by construction. `nylium.tables.base` remains
   only as a compatibility re-export.
4. **`nylium/table_rows/` is deleted.** If a future pair truly cannot be
   split without a cycle, that pair — and only that pair — may land in
   `table_rows/` with a comment naming the cycle. The package is not a
   dumping ground.
5. **Package `__init__.py` files are re-export conveniences, not the
   persistence contract.** Because the contract is one-class-per-file,
   consumers import the owning leaf module; `__init__.py` re-exports exist so
   `import nylium.tables` / `import nylium.rows` still registers every mapping.

## Consequences

- The dependency direction is `database.registry ← rows ← tables ← consumers`.
- There are no `TABLE_*` symbols and no `nylium.table_rows` imports.
- Static cycle suppression stays off: `pyproject.toml` must not reintroduce
  `reportImportCycles=false` for this layer.

Gates: `uv run basedpyright` → 0/0/0, `uv run ruff check src tests` → clean,
`uv run pytest -q` → 295 passed, plus an AST structural check: one class per
file, file stem = snake_case(class), no `table_rows`, no `TABLE_*`.
