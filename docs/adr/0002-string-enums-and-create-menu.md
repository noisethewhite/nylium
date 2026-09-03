# ADR-0002: String enums + "+" creation menu

Status: accepted (2026-09-03, with amendments: option rename
propagates to stored values; "New object" creates with empty name)
Date: 2026-09-03

## Context

Two asks in one:

1. The sidebar "+" currently jumps straight into the create-type form.
   It should open a small menu: **New type / New object / New enum**.
2. nylium has no enum concept. A prop today is either a scalar, an
   object link, or an array of those. User wants **string enums**: a
   type whose value is one of a fixed list of strings (e.g. `Status`
   = `active | paused | archived`), usable as a prop type.

## Decisions

### Enum model (backend)

1. **An enum is a user type** — a row in `types`, like any user type:
   own name, icon, color, deletable, renamable through the existing
   paths. Plural form is meaningless for enums → `plural_name` stays
   NULL, which also keeps `rename_type`'s builtin-guard semantics: we
   extend the guard to enums where identity edits are allowed (rename,
   icon, color) but prop edits are not (enums have no props).

2. **New column `types.kind`**: `Text, nullable=False, server_default
   "object"` — values: `object`, `enum`. Builtins and array types keep
   `object` (they're distinguished by `plural_name IS NULL` /
   `Array<…>` naming as today). Added via the established idempotent
   `ALTER TABLE … ADD COLUMN IF NOT EXISTS` in `_ensure_schema` — no
   manual SQL on prod.

3. **New table `enum_options`** (one file per table —
   `tables/enum_options.py`):
   - `uuid` pk (default uuid4)
   - `type_uuid` FK → `types.uuid` `ondelete="CASCADE"`, not null
   - `value` Text, not null
   - `position` Integer, not null, default 0 — display/order-stable
   - `UniqueConstraint("type_uuid", "value")` — no duplicate options
   within an enum

4. **Value storage: reuse `string_values`.** An enum-typed prop is a
   string under the hood. No new value table, no changes to the
   object-layer read/write paths beyond validation.

5. **Validation on write**: where the object layer validates a scalar
   by `PYTHON_TYPE`, an enum prop validates membership: value must be
   one of the type's `enum_options`. Violation → `TypeError` in the
   object layer, mapped to 400 by the HTTP layer like existing
   validation errors. None/unset passes (existing unset semantics).

6. **API additions** (`api.py` + `routes.py`, mirroring existing
   verbs):
   - `create_enum(name, options: list[str], icon, color) -> TypeView`
     — requires ≥1 non-empty unique option
   - `sync_enum_options(name, items: list[tuple[UUID | None, str]])
     -> TypeView` — applies the editor's full option draft at once,
     mirroring `sync_props`: a matching uuid renames that option in
     place (the rename **propagates to stored values** — since values
     live in `string_values` as plain strings, one UPDATE rewrites
     them), None creates a new option, options absent from the draft
     are deleted — **deletion refuses while the option is still in
     use** by any instance (ValueError, like delete_type)
   - `TypeView` gains `kind: str` and `enum_options: list[str] | None`
   - `create_type` / `sync_props` accept enum type names as prop value
     types unchanged (they already go through `WType.ensure` — but
     ensure must NOT silently create an object type when the caller
     names an enum, and vice versa; kind is checked on mismatch)

7. **Deletion**: `delete_type` unchanged for instances; enum deletion
   is additionally blocked while any prop references it (existing FK
   on `props.value_type_uuid` already does this).

8. **Python layer**: no `WEnum` marker class — enums are user-defined
   at runtime, there is no static python peer. In `WTypeMeta`-generated
   classes enum props annotate as `str`. Validation lives in the
   prop-set path (`wprop`/`wobject` setattr), next to
   `WScalar.validate`.

### Frontend

9. **"+" menu**: a popover (same pattern as `IconPicker`) with three
   rows — New type / New object / New enum.
   - New type → existing create-type tab (unchanged)
   - New enum → new create-enum form: name, icon/color picker, an
     editable list of option strings (add/remove/reorder rows)
   - New object → type picker restricted to `kind=object` user types,
     then `create_object(name=<empty>)` and open the object editor —
     matches the current "create from type view" flow

10. **Enum prop editor**: a dropdown (`<select>`-style control like
    `TypePicker`) listing the type's `enum_options`, plus an empty
    "—" choice for unset. No free text.

11. **Type views**: enum types render in the sidebar with their icon
    like other types; opening an enum type shows its option list
    (editable via sync_enum_options) instead of a prop schema. Object
    lists don't apply (enums have no instances).

## Consequences

- `types` gains a column; prod migrates itself on restart (same
  pattern as icon/color).
- Enum options can't be deleted while in use, but they CAN be renamed:
  the rename rewrites stored `string_values` rows in the same
  transaction (values are plain strings keyed by prop — one UPDATE per
  renamed option).
- "New object" creates the object immediately with an empty `name`
  prop and opens its editor — no intermediate form.
- Arrays of enums work for free (`Array<Status>` — element validation
  recurses into the same check).

## LOC estimate

Backend ~250 (table, kind column, validation, API, routes, tests).
Frontend ~250 (menu, create-enum form, enum dropdown editor, type
view variant). Over the 250-LOC bar — implementation starts only
after this ADR is approved.
