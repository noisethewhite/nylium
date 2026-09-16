# ADR-0024 — Conditional expressions in the formula DSL

Status: Accepted
Date: 2026-09-16

## Context

`Fee.effective` must fold to a different value depending on `Fee.kind`
(an enum: `tax` vs `discount`): a tax adds `basis * rate`, a discount
subtracts it. The formula DSL (ADR-0005/0022/0023) has arithmetic and
aggregates but no branch — so `effective` cannot be a formula today and
would need a bespoke mechanism.

## Decision

Add a conditional expression to the formula language:

```
IF(<prop> <op> <literal>, <then>, <else>)
```

- `<prop>` — a **sibling scalar prop** of the owner (String, enum,
  Numeric or Integer; arrays and the other scalar families are rejected).
- `<op>` — `==` or `!=`.
- `<literal>` — a double- or single-quoted string for String/enum, or a
  numeric literal for Numeric/Integer.
- `<then>` / `<else>` — any valid expression (arithmetic, aggregates,
  prop-to-prop, and a nested `IF`).

Read-time semantics: compare the owner's stored `<prop>` value against the
literal; when it matches `==` (or fails `!=`) the formula folds to
`<then>`, otherwise `<else>`. An unset `<prop>` is *not equal* — it falls
through to the else branch (consistent with the ADR-0005 unset rule).

Example (the Fee case):

```
effective = IF(kind == "tax", basis * rate, -basis * rate)
```

## Validation

At save, the cond is refused unless:

1. `<prop>` exists on the owner and is a scalar (not `Array<T>`);
2. its value spec is String, an enum, Numeric, or Integer;
3. `<literal>` is a string for String/enum, a number for Numeric/Integer;
4. `<then>`/`<else>` validate as ordinary numeric expressions (the
   existing rules apply recursively).

No boolean `AND`/`OR` — one comparison per `IF` keeps the DSL from
becoming a condition engine; compose with nesting when more is needed.

## Consequences

- `Fee.effective` becomes a plain formula, no new prop kind.
- Rename-rewrite rebinds the cond prop and the then/else refs: the cond
  prop is a sibling reference, so it must be included in
  `Formula.sibling_references`.
- `IF` is evaluated read-time in `evaluation.evaluate_ast`, so it costs
  nothing on write.
- Nested `IF` is permitted but rare; both branches stay in the AST (no
  short-circuiting of aggregates in the non-taken branch at parse time).
