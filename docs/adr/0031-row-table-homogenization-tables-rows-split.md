# ADR-0031: Homogenize every `TABLE_*` onto the Row/Table pattern and split `tables` / `rows`

- Status: proposed
- Date: 2026-09-20

## Context

There are 30 `TABLE_*` mapped dataclasses (`@reg.mapped_as_dataclass`, ADR-0012).
Fifteen of them — the domain objects (`types`, `instances`, `props`, `traits`,
`type_traits`, `enum_options`, `unit_parts`), the decor tables, `files`, and the
auth tables — already follow the three-layer pattern:

```
TABLE_*          mapped dataclass (raw ORM row)         tables/…/table_*.py
Row              writable snapshot (read)                tables/…/<name>.py
Table[K, Row]    Mapping store + business operations     tables/…/<name>s.py
```

The other fifteen have **no** Row/Table: their SQL lives directly in the
objects layer as module-level statement helpers (ADR-0030 phase C moved them
there from `tables/`). They are the nine scalar value tables
(`string/integer/numeric/boolean/datetime/date/time/monthday/monthdaytime_values`),
the three link value tables (`array_values`, `instance_values`, `file_values`),
and the three function tables (`function_nodes`, `function_edges`,
`instance_function_links`). Today they are read/written through raw
`sqla.select/insert/update/delete` + `Database.*` in `scalars/`,
`objects/warray_values.py`, `objects/wlink.py`, `objects/wfile.py`, and
`objects/wfunction/`.

Max wants uniformity — every table on the Row/Table pattern — and the Row
classes split out of `nylium/tables` into a sibling `nylium/rows` package.

## Decision

1. **Give each of the fifteen remaining tables a Row + Table.** Row is the
   typed read snapshot; Table is the `Mapping[K, Row]` store that owns the
   business operations currently scattered as module-level helpers
   (`read`/`write`/`clear`, `add_element`/`delete_elements_of`,
   `link_for`/`merge_link`, `nodes_of`/`edges_of`/`sync_graph`, …).
2. **Composite-PK tables** (`(inst_uuid, prop_uuid)`, `(inst_uuid, index)`)
   type their Table as `Table[tuple[K, K], Row]` — the `TypeTraits` precedent.
   `Row.persist` stays single-PK-only; composite-PK tables write through
   Table-store methods, never through Row write-through.
3. **Split the package.** All Row classes move to `nylium/rows/` (mirroring the
   `objects/` / `values/` / `decor/` / `functions/` / `auth/` subpackages).
   `nylium/tables/` keeps `TABLE_*` (mapped dataclasses) and the Table stores.

## Naming

`TABLE_StringValues` → `StringValue(Row)` + `StringValues(Table)`, and so on
for all fifteen. Composite-PK stores keep the plural-of-row name convention
(`ArrayValues`, `InstanceValues`, `FunctionNodes`, …).

## Consequences / risks

- **Cross-package import cycle.** Row classes need `TABLE_*` for `__table__`;
  Table stores need the Row class for `__row__`. After the split this is a
  `rows ↔ tables` cycle, not the current intra-package cycle. Mitigation:
  `rows/__init__.py` and `tables/__init__.py` import order is load-bearing
  (same discipline ADR-0012 already documents for `database/table.py`), and
  the few genuinely cyclic spots keep their lazy in-function imports.
- `scalars/` becomes a thin delegation layer over the new value Table stores
  (the `WScalar.SCALAR` link from ADR-0030 keeps pointing at the scalar peer
  classes, which now call `StringValues.read/write/clear` instead of raw SQL).

## Migration plan

- **Phase 1** — nine scalar value tables → Row + Table; rewrite `scalars/`
  (base + ten peers) to delegate into the stores.
- **Phase 2** — three link value tables → Row + Table; rewrite
  `warray_values.py`, `wlink.py`, `wfile.py`.
- **Phase 3** — three function tables → Row + Table; rewrite
  `wfunction/graph.py` and `wfunction/function_links.py`.
- **Phase 4** — package split: move every Row class into `nylium/rows/`,
  leave `TABLE_*` + Table stores in `nylium/tables/`, fix the import surface.

Gates after **every** phase (never only at the end):
`uv run basedpyright` → 0/0/0, `uv run ruff check src` → clean,
`uv run pytest` → 295 passed.
