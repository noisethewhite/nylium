# ADR-0022: Prop-to-prop formulas and unit results

Status: proposed
Date: 2026-09-15

## Context

ADR-0005 gave props computed formulas over the owner's own `Array<T>`
props only (`SUM(items.price) * 1.21`). Two real models are out of reach:

1. **Inline line-item math.** With `Array<Embedded>` (ADR-0021) a
   `Receipt` owns inline `ReceiptItem` children. Each child's
   `line_total` is `price * quantity` — a formula over the child's
   *own sibling props*, not an array aggregation. There is no array to
   aggregate; the inputs are the element's own scalar props.
2. **Unit-aware results.** A formula prop typed `Numeric<Unit>` (e.g.
   `Currency`) must yield a `Quantity`, not a bare `Decimal`. Today a
   formula prop can only be `Numeric` (or `Integer` for a bare
   `COUNT`), so `line_total: Currency = price * quantity` is rejected
   at prop save.

## Decisions

### Syntax: bare identifiers are sibling references

1. The grammar gains one production: a bare `IDENT` that is not a
   function call is a **sibling reference** to another prop of the
   same owner. The AST gains a `Ref(key)` node.

   ```
   factor := NUMBER | '(' expr ')' | FUNC '(' path ')' | IDENT | '-' factor
   ```

   `line_total = price * quantity` parses to
   `BinOp('*', Ref('price'), Ref('quantity'))`. A `Ref` never takes a
   dotted path and never refers to an array prop (arrays stay
   aggregate-only via `SUM/AVERAGE/COUNT/MIN/MAX`).

2. Validation: a `Ref` must name an existing prop of the owner
   (`owner_type_props`) that is numeric — `Integer`, `Numeric`, or
   `Numeric<Unit>`. Array props, non-numeric props, and unknown props
   → 422 with a precise message. Referencing another *computed* prop
   is not separately rejected (schema validation only sees value
   types, not formula flags); at read time it folds as the referenced
   prop's stored value, which for a computed prop is never set, so it
   counts as 0. Chained formulas stay out of scope.

3. Rename-rewrite: a renamed sibling key rewrites `Ref` nodes in the
   same transaction as array keys. The existing local pass
   `Formula.rewrite(formula, renames, …)` already receives the full
   owner-prop rename map, so the `Ref` branch reuses that first
   argument unchanged.

### Evaluation: scalars alongside arrays

4. `Formula.evaluate(formula, arrays, scalars)` also takes
   `scalars: Mapping[key, Decimal | Quantity | None]` — the referenced
   siblings' stored values. `evaluate_ast` folds a `Ref` to
   `scalars[key]` (unset → 0, matching the ADR-0005 missing-ref rule).
   Array aggregations are unchanged.

### Unit results: Quantity promotion

5. Arithmetic promotes to `Quantity` when either operand is a
   `Quantity`: the magnitudes fold with `Decimal` arithmetic and the
   result carries the source `Quantity`'s unit part (the left
   operand's when both are quantities). `price` (a `Numeric<Currency>`
   read, which surfaces as `Quantity(display, part)`) times `quantity`
   (a bare `Decimal`) is therefore `Quantity(display*quantity, part)`.
   A formula over only bare decimals stays `Decimal`.

6. A formula prop may now be typed `Numeric<Unit>`.
   `_check_formula_prop` admits unit-numeric value types. At render,
   `_eval_formula` wraps the result: a `Quantity` result renders
   `ScalarValue(value=result.value, unit=result.unit)`; a bare
   `Decimal` result on a unit prop renders with `unit=None` (base
   part). `Integer` props keep the bare-`COUNT` rule and render `int`.

## Out of scope (phase 2)

- Conditionals in the DSL (`IF`, kind/basis logic).
- `SUM`/aggregates over `Array<Embedded>` elements — how embedded
  arrays feed `arrays` is a separate decision.
- Formulas referencing other formulas (chained evaluation /
  topological order).
- Unit arithmetic across different units (no conversion; the left
  operand's part is carried through).

## Consequences

- Parser, AST and evaluator each grow one branch; no storage migration
  (formulas remain validated text).
- A `Ref` read is one `getattr` on the owner wrapper, so a sibling ref
  costs one value read per ref — negligible.
- The wire shape for a unit formula prop is the ordinary
  `Numeric<Unit>` shape (`{value, unit}`), so the frontend renders it
  with the existing unit cell unchanged.
