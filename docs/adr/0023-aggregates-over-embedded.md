# ADR-0023: Aggregates over Array<Embedded> and chained member formulas

Status: proposed
Date: 2026-09-16

## Context

ADR-0021 gave arrays embedded (composition) elements, ADR-0022 gave
prop-to-prop formulas and unit results. Two gaps keep a `Receipt`'s
`subtotal` out of reach:

1. **Aggregates drop the unit.** `_eval_formula` folds a member cell to
   its magnitude (`value.value`) before the aggregator sees it, so
   `SUM(lines.price)` over a `Numeric<Currency>` member returns a bare
   `Decimal`, not a `Quantity`.
2. **Aggregates can't read computed members.** A member prop like
   `line_total` is computed (never stored), so `getattr(member,
   "line_total")` is `None` and folds to 0. `subtotal =
   SUM(lines.line_total)` is therefore always 0.

## Decisions

### Unit-preserving member cells

1. An array row's cell type widens from `Decimal | None` to
   `Decimal | Quantity | None` — a `Quantity` keeps its part name.
   `_sibling_cell` already normalizes stored values without collapsing
   the part, so member cells reuse it verbatim. Aggregators become
   quantity-aware:

   - **SUM** — if any cell is a `Quantity`, the result is
     `Quantity(sum of magnitudes, part of the first quantity)`; all
     elements share one member type so parts agree. Otherwise a plain
     `Decimal`.
   - **AVERAGE** — SUM divided by the row count; a quantity result
     keeps its part.
   - **MIN / MAX** — compare by magnitude, return the winning cell as
     is (a `Quantity` stays a `Quantity`).
   - **COUNT** — unchanged (row count / non-null cell count).

### Chained member formulas

2. When a member prop of an array element has a formula, building that
   cell folds the element's own formula over its sibling props — the
   same `_evaluate_formula` path, one level down. This is deliberately
   a single chained level: a member formula is sibling-ref-only
   (`line_total = price * quantity`). A formula that itself references
   another computed prop stays out of scope (ADR-0022 already deferred
   topological ordering).

### Embedded arrays feed `arrays` like ref arrays

3. `getattr(wrapper, array_key)` already returns embedded children as
   `WObjectShape`, so no new input plumbing — the only differences are
   the two rules above, applied uniformly to every array element. Ref
   elements (`Array<Person>`) have neither quantity nor computed member
   props in current models, so the change is inert there.

## Consequences

- Reading a formula prop that aggregates over a computed embedded
  member costs O(N) single-level folds (N = element count) — fine at
  nylium scale, and still read-time/consistent (no denormalization).
- No storage migration: formulas remain validated text, cells are
  rebuilt per read.
- A formula prop typed `Numeric<Unit>` aggregating quantities renders
  the ordinary `{value, unit}` shape (ADR-0022 rule 6 already handles
  the wrapping).

## Out of scope (phase 2)

- Conditional DSL (`IF`, kind/basis logic) — ADR-0024.
- Topological chained evaluation (a computed prop feeding another
  computed prop at the owner level).
- Unit conversion across differing parts inside one aggregate.
