# ADR-0003: User-defined units of measure

Status: accepted (2026-09-03; supersedes the original Pint-based
proposal — the user redirected the design to user-managed Unit
entities before implementation began)
Date: 2026-09-03

## Context

Numeric props are bare magnitudes. The user wants units with
conversion, defined **by the user**, not from a built-in registry:

- A **Unit** is created from the sidebar "+" menu ("New unit"), like
  types and enums.
- A Unit has one **base part** and any number of **secondary parts**.
  A secondary has: name, multiplier, offset.
  Example: Temperature — base `°C`; secondary `°F` with multiplier 1.8
  and offset 32 (F = C × 1.8 + 32).
- When a numeric prop (Decimal/Integer) is added to a type, it gets a
  **unit selector with default None**.

## Decisions

### Unit model (mirrors ADR-0002 enums)

1. **A unit is a user type** — a row in `types` with
   `kind = 'unit'`. Own name, icon, color; renamable/deletable through
   existing paths. No props, plural_name NULL (like enums).

2. **New table `unit_parts`** (`tables/unit_parts.py`, one file per
   table):
   - `uuid` pk (default uuid4)
   - `type_uuid` FK → `types.uuid` `ondelete="CASCADE"`, not null
   - `name` Text, not null — `°C`, `kg`, `lb`
   - `multiplier` Float, not null, default 1
   - `offset` Float, not null, default 0
   - `is_base` Boolean, not null, default False — **exactly one base
     part per unit**, enforced in the API layer
   - `position` Integer, not null, default 0 — display order
   - `UniqueConstraint("type_uuid", "name")`

3. **Conversion is linear**, no external registry (Pint dropped):
   - to canonical (base): `canonical = (entered − offset) / multiplier`
   - from canonical: `display = canonical × multiplier + offset`
   - Base part: multiplier 1, offset 0 → identity.

### Prop typing

4. **Unit is an optional parameter of numeric builtins**:
   `Decimal<Temperature>` / `Integer<Temperature>` in the prop-spec
   grammar (angle brackets like `Array<…>`). Bare `Decimal`/`Integer`
   = unit None — unchanged behavior, no migration of existing props.
   The parameter must name a type with `kind='unit'`; validated on
   prop create/sync.

5. **Type editor**: numeric prop rows show a unit picker (search
   field, like every picker) listing unit types, default "None".

### Storage

6. **Existing `numeric_values` table**, two-column shape:
   - `value` stores the magnitude in the **base part** of the prop's
     unit (canonical). Comparisons/sorting/future formula arithmetic
     need no conversion.
   - `unit` (**new** `Text, nullable`; idempotent
     `ALTER TABLE … ADD COLUMN IF NOT EXISTS` in `_ensure_schema`)
     stores the part name **as entered**. NULL = plain number; all
     existing rows stay valid.

7. **Reads return the value converted back into the stored `unit`**
   plus the unit name — display shows what was entered (`1500 g`
   stays `1500 g`).

### Write path

8. Input is a number plus an optional part name (UI: numeric input +
   unit picker defaulting to the base part). Validation:
   - part name must belong to the prop's declared unit type → else
     `ValidationError` (422);
   - unit-typed prop with no part name → base part assumed;
   - plain numeric prop keeps the current shape (no unit field).

9. **Renaming a part propagates** to stored `numeric_values.unit`
   strings in the same transaction (same rule as enum option renames).
   **Editing multiplier/offset does not rewrite stored values** —
   canonical magnitudes were physical at entry time; only future
   display conversion changes.

10. **Delete-in-use**: a unit type referenced by any prop spec
    (`Decimal<Name>` / `Integer<Name>`, also inside `Array<…>`)
    cannot be deleted → 409, same machinery as enum delete-in-use.

### Cross-unit semantics

11. Units are only comparable **within the same unit type**. There is
    no dimension algebra (`kg × m/s²`); mixing different unit types in
    one prop or (later) one formula is a validation error. This keeps
    the model honest without a dimension registry.

## Consequences

- No new dependencies; conversion is one multiply/subtract.
- Arrays of unit-typed numerics (`Array<Decimal<Temperature>>`) work
  once the param grammar parses nested params.
- Computed props (ADR-0004) inherit canonical-only arithmetic: formula
  math runs on base-unit magnitudes, results convert at display.
- The automation/integrations layer (iCloud/CalDAV etc.) is future
  scope and unaffected.

## Open questions

- Compound entry (`1 m 82 cm`) — no; single part per value.
- Negative offsets / logarithmic scales (dB) — linear model only;
  dB-style units are out of scope until asked.
