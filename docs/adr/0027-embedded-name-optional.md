# ADR-0027: Optional `name` prop for embedded composition types

## Status

Accepted — 2026-09-17

## Context

Every type is created with a pinned `name` prop as its first prop; the
API boundary (`create_type`, `sync_props`, `reorder_props`) enforces it
and `WEmbedded` writes a generated name (`"<parent> → <prop key>"`) into
each embedded child on every write.

That model assumes a composition child is identified by a name. But some
embedded elements are identified by *what they point at*, not by a label.
A receipt line (`ReceiptItem`) is "this product, this price, this
quantity" — it references a `Product` and has no meaningful name of its
own. Forcing a `name` prop onto it is noise: the UI shows a column nobody
cares about, and the generated `<parent> → <prop key>` label duplicates
information already carried by the `product` ref.

## Decision

Embedded composition types may omit the `name` prop entirely. The
`name`-pinned-first invariant stays for **standalone** types (which are
listed and addressed by name); it is relaxed only for `embedded=True`:

- `create_type` / `sync_props` / `reorder_props` no longer require
  `name` to be present (or first) when the owner type is embedded.
- `WEmbedded._write_generated_name` becomes a no-op for name-less
  embedded types — the child keeps its registry name
  (`<TypeName>:<shortuuid>`), which is already unique and stable.
- Display paths that read `name` for a label (`ObjectView.ref_label`,
  tag/array rendering) fall back to the registry name or the referenced
  object's label when the prop is absent; they never `__getattr__` a
  missing prop (the wrapper raises `AttributeError` on unknown props).

The `→` generated-name machinery (ADR-0004/ADR-0021) is unchanged for
embedded types that *do* keep a `name` prop.

## Consequences

- Name-less embedded elements are not addressable by a user label; they
  are addressed by their ref members (e.g. `ReceiptItem.product`). The
  read-side backlink/array view still renders them by registry name.
- Any code that assumed `name` is present on every type must guard the
  read; the api layer now centralises that guard instead of scattering
  `getattr(..., "name")` checks.
- No migration: relaxing a validation invariant, not changing storage.
  Existing embedded types with a `name` prop are unaffected.

## Alternatives considered

- *Keep `name` mandatory, hide it in the table UI* — rejected: the prop
  would still occupy storage, still be regenerated on every write, and
  still leak into views; hiding it in the UI is a cosmetic fix for a
  modeling error.
- *Give every embedded type a synthetic `id` prop instead* — rejected:
  the registry name already provides a stable, unique identity; a
  dedicated prop adds storage and a second identity source for no gain.
