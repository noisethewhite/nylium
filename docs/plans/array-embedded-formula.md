# Plan: Array<Embedded> + formula expansion (Receipt model)

Status: in progress (orchestrated via subagents)
Date: 2026-09-15

## Goal

Make the Receipt model work on real nylium. Two features:

1. **`Array<Embedded>`** — an array prop whose element type is an embedded
   (composition) type, rendered as a `<Table>` in the UI. ADR-0021.
2. **Formula expansion** — prop-to-prop formulas within the owner + a
   unit-typed result (`Currency`, not `Decimal`). ADR-0022.

## Final model (decided with Max)

- `Shop` — standalone ref.
- `Product` — standalone ref + traits `edible` / `consumable`.
- `Receipt` — standalone: `date: DateTime`, `shop: Ref<Shop>`,
  `items: Array<ReceiptItem>`, `fees: Array<Fee>`.
- `ReceiptItem` — embedded: `product: Ref<Product>`, `price: Currency`,
  `quantity: Numeric`, `line_total` (computed).
- `Fee` — embedded: `kind: Enum[tax, discount]`, `basis: Enum[percent, fixed]`,
  `rate: Numeric` (if percent), `amount: Currency` (if fixed),
  `effective` (computed). No domain Union (absent in nylium) — use two enums.

Computed values (read-time, ADR-0005 pattern): `line_total = price*quantity`,
`subtotal = SUM(items.line_total)`, `total = subtotal + SUM(fees.effective)`.

## WIP state on disk (uncommitted, `git diff` in ~/projects/nylium)

Feature #1 backend is ~80% done. Modified files:

- `src/nylium/api/shared.py` — lifted the `Array<Embedded>` ban (was a
  ValidationError; `_normalize_value` already recursed embedded drafts).
- `src/nylium/objects/warray.py` — `_box` / `_destroy_box` / `_box_embedded`
  now handle embedded elements (owned by the array instance, named
  `<parent> → <prop key> #<index>`).
- `src/nylium/objects/wembedded.py` — new public `create_array_element`.
- `tests/test_embedded.py` — 4 new tests (`team_type` helper +
  round-trip / rewrite / cascade / empty-clear).
- `docs/adr/0021-array-embedded.md` — new ADR.

pyright: 0 errors, 0 warnings. Tests: 17 passed, 1 FAILED —
`test_array_of_embedded_empty_and_clear` fails on its last assertion
(clearing the array with `None`):

```
TypeError: array prop takes list, got NoneType
src/nylium/api/shared.py:198 (_normalize_value, array branch)
```

Root cause: `_normalize_value`'s array branch requires `list` and never
handles `None`. Clearing an array prop via `None` is unsupported today
(pre-existing gap, exposed by the new test).

## Remaining work (feature #1 backend — hand to subagent 1)

1. **Fix `None` normalization for array props** in `src/nylium/api/shared.py`
   `_normalize_value` (~line 194-204): accept `None` and return `None` (unset),
   mirroring how scalar/embedded/ref branches treat None. Confirm `[]` still
   means "empty" and `None` means "unset". Add/keep a test for both.
2. **Name regeneration on parent rename** — `WEmbedded.regenerate_names`
   (src/nylium/objects/wembedded.py) walks embedded (link) props only; extend it
   to also regenerate element names for `Array<Embedded>` props (an element's
   name is `<parent> → <prop key> #<index>`). Add a test mirroring
   `test_sync_props_rename_regenerates_names` for an array.
3. **`sync_props` sweep for Array<Embedded>** — dropping/retyping an
   `Array<Embedded>` prop must delete its elements. `destroy_children_of_prop`
   walks `instance_values` links, but array elements live in `array_values`
   (owner = the array instance, not the parent). Verify the cascade and add a
   test mirroring `test_sync_props_delete_destroys_children`.

## Gates (must all pass before commit)

- `uv run basedpyright` → `0 errors, 0 warnings, 0 notes`
- `uv run pytest -q` → all green (currently 246+ tests)
- Commit with a clear message, e.g. `feat: Array<Embedded> composition (ADR-0021)`.

## Out of scope for subagent 1 (next phases)

- Formula expansion (ADR-0022) — separate subagent, separate files.
- Frontend `<Table>` render of `Array<Embedded>` — depends on feature #1 backend.
- Seeding Receipt/Product/Fee on prod + e2e — final phase.

## Do NOT touch

- Prod (`https://nylium.noisethewhite.dev`), VPS `remotemalina-jump`.
- Foreign local ports 8474, 8490.
- `databasemethod`, `Array<Book>` builtin type.
- Nested `Array<Array<Embedded>>` — explicitly deferred (ADR-0021 phase 2).
