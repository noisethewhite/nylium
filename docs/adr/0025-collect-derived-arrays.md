# ADR-0025 — Collect: derived arrays over a range predicate

Status: Accepted
Date: 2026-09-16

## Context

Analytics over receipts (and any ordered scalar) must live inside nylium, not
in an external CSV/pandas chore. The user wants an object such as:

```
Period {
  from:     Date
  to:       Date
  receipts: Array<Receipt>   ← derived, not stored
  total:    Numeric<Currency> = SUM(receipts.subtotal)
}
```

`receipts` must *always* reflect the current set of `Receipt` objects whose
member prop falls within `[from, to]` — with no write hooks and no
denormalized state to invalidate (the ADR-0005 §129 invariant).

The user's two constraints:
1. The range predicate must generalize **beyond dates** — any ordered scalar.
2. The cost is read-time only, and must be cheap (an indexed range scan, not a
   full table scan).

## Decision

A third kind of computed prop, **collect**, sits beside `formula` (scalar,
ADR-0005) and `function` (DAG, ADR-0007):

- `collect` is a `TEXT` column on `props`, mutually exclusive with `formula`
  and `function_uuid`.
- A collect prop's value type must be `Array<T>`.
- `collect` holds the **key of an ordered scalar member prop** of `T`.
- The owner type must define `from` and `to` props of the **same** value spec.
- At read time the array is derived as:

  > every `T` instance whose member prop value `v` satisfies
  > `owner.from <= v <= owner.to`.

`collect` is a **range (`BETWEEN`) over an ordered scalar**, deliberately *not*
an arbitrary `WHERE`. Equality, `contains`, strings and grouped analytics stay
out of the core — this is the whole boundary that keeps it from becoming
mini-SQL.

### Ordered scalars

`collect` accepts a member prop whose value spec is one of:

- `Numeric`, `Integer`, `Date`, `Datetime`, or any `Numeric<Unit>`.

Each maps to its stored value table for the range scan:

| spec              | table               | comparison value |
| ----------------- | ------------------- | ---------------- |
| `Numeric`         | `numeric_values`    | `Decimal`        |
| `Numeric<Unit>`   | `numeric_values`    | `Decimal` (magnitude; unit ignored) |
| `Integer`         | `integer_values`    | `int`            |
| `Date`            | `date_values`       | `date`           |
| `Datetime`        | `datetime_values`   | `datetime`       |

`Numeric<Unit>` bounds (`from`/`to`) are `Quantity`; the fold compares the
canonical magnitude only.

### Validation

At save (`create_type` / `sync_props`), a collect prop is refused unless:

1. its value type is `Array<T>`;
2. `T` exists and is **not embedded** (embedded children are composition, not
   standalone rows to collect);
3. the member prop named by `collect` exists on `T` and is an ordered scalar;
4. the owner defines `from` and `to` props with exactly the member's value spec.

### Read-time derivation

`props.collect` is read in `ObjectView.from_uuid` and in formula folding
(ADR-0023) via one reverse query per collect prop:

```sql
SELECT inst_uuid FROM <value_table>
 WHERE prop_uuid = :member_prop AND value BETWEEN :lo AND :hi
```

The `value` column is indexed in practice (the per-prop value tables are
primary-keyed on `(inst_uuid, prop_uuid)`), so the scan is a narrow range on a
small table — `O(log N + K)`, not a full scan. Writes (`Receipt` create/update)
do nothing: there is no hook and no stored array, so the cost is read-only, and
only when a `Period` is actually opened.

A collect prop is **read-only**: `_normalize_props` refuses writes exactly like
`formula`/`function` props.

## Consequences

- `total = SUM(receipts.subtotal)` works immediately: ADR-0023 already folds
  over derived arrays once `receipts` is materialized as a list of members
  (each member's computed `subtotal` is evaluated one level down).
- The reverse projection (`tags`/`backlinks`) is unchanged — a collect array is
  a *read* projection, not stored membership, so it does not appear in the
  stored array membership index. That is correct: collect is a query, not a
  link.
- `Array<Embedded>` collect is out of scope (embedded elements are not
  standalone query targets). Aggregate over `Array<Embedded>` is ADR-0023;
  aggregate over a collect array is `SUM(receipts.…)` on top of this.
