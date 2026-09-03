# ADR-0003: Units of measure for numeric props

Status: proposed (2026-09-03)
Date: 2026-09-03

## Context

Numeric props are currently bare magnitudes: `Decimal` and `Integer`
store a number with no notion of *what* it measures. The user wants
units and conversion as the first step toward computed values
(ADR-0004): `weight = 1.5 kg`, entered as `1500 g` or `3.3 lb`,
stored correctly, displayed sensibly, and rejected when the dimension
is wrong (kilograms where metres are declared).

This is the data-layer slice only. Integrations/automation are a
later phase (out of scope here, recorded in Engram).

## Decisions

### Type model

1. **Unit is a parameter of the numeric builtin, not a composite
   object.** Prop type grammar gains `Decimal<unit>` / `Integer<unit>`
   (same angle-bracket syntax as `Array<…>`). `unit` is any unit the
   backend registry parses: `kg`, `m`, `s`, `L`, `m/s`, `°C`.
   Bare `Decimal` / `Integer` stay param-less and behave exactly as
   today — no migration of existing props.

2. **The dimension is derived from the declared unit**, not declared
   separately: `Decimal<kg>` → mass. Pint resolves this; we store the
   unit string as-is in the prop spec.

### Conversion engine

3. **Pint on the backend** (`pint` added to `pyproject.toml`). One
   `UnitRegistry` per process. Pint gives parsing (`"3.3 lb"`),
   conversion, and dimensionality checks (`kg + m` →
   `DimensionalityError` → our `ValidationError`). We do not write our
   own conversion tables.

4. **Currencies are explicitly out of scope.** EUR/USD are not units —
   they are floating exchange rates and need a rate provider, fetching
   policy, and staleness semantics. Separate ADR if ever.

### Storage

5. **Canonical value + display unit, two columns on the existing
   `numeric_values` table** (no new table):
   - `value` (existing) now stores the magnitude in the dimension's
     **base unit** (Pint's SI base for that dimension: kg, m, s, …).
     Comparisons, sorting, and future formula arithmetic work on
     `value` directly with zero conversion.
   - `unit` (**new** `Text, nullable`, idempotent
     `ALTER TABLE … ADD COLUMN IF NOT EXISTS` in `_ensure_schema`)
     stores the unit **as entered by the user**. NULL = plain number,
     which keeps every existing row valid unchanged.

6. **Display renders the entered unit**: the UI converts `value` back
   into `unit` for display. Entering `1500 g` on a `Decimal<kg>` prop
   stores `value=1.5, unit="g"` and renders back as `1500 g`, not as
   `1.5 kg`. What you typed is what you see.

### Write path

7. **Input accepts `number` or `number + unit`** (`"500"`, `"500 g"`,
   `"3.3 lb"`). A bare number means the prop's declared unit. An
   explicit unit must parse and its dimension must match the declared
   unit's dimension — otherwise `ValidationError` (422) with a human
   message ("expected a mass, got metres"). This validation happens
   next to the existing `PYTHON_TYPE` scalar checks in the object
   layer.

8. **Wire format**: `ScalarValue` for unit-typed props carries the raw
   input string; the backend normalizes to canonical+unit before
   write. Reads return `{value, unit}` so the frontend renders without
   its own unit math. (Exact `ScalarValue` shape pinned down at
   implementation; contract change is additive.)

### Frontend

9. Unit-typed numeric props render with the unit next to the value
   (label suffix in the input box, like the existing `key → Type`
   pattern). The draft input parses free text; invalid unit text
   surfaces through the existing error banner.

10. Editing a prop's declared unit on an existing type: allowed only
    within the same dimension (`kg` → `g` re-displays existing rows;
    `kg` → `m` is refused, like a type change that would invalidate
    stored data).

## Consequences

- Numeric reads/writes for unit-typed props pay one Pint conversion
  each way; negligible at our scale.
- Formulas (ADR-0004) inherit dimension checking for free: adding
  `kg` to `m` fails in Pint before any formula semantics exist.
- `Integer<unit>` keeps integer storage; conversions that produce
  non-integers (`1 kg` entered as `2.2 lb`) are refused for
  `Integer<…>` — use `Decimal<…>` for convertible quantities.
- Sorting/filtering (when it arrives) works on canonical `value`
  without unit awareness.

## Open questions

- Compound display (`1 m 82 cm`) — no; single unit per value.
- Imperial-by-default types (`Decimal<lb>`) — allowed, canonical is
  still SI; Pint converts both ways.
- `°C`/`°F` offsets (affine units) — Pint handles them; if edge cases
  bite, restrict v1 to multiplicative units.
