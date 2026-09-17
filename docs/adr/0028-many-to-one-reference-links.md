# ADR-0028: Many-to-one reference links

## Status

Accepted — 2026-09-17

## Context

`instance_values` stores every object reference (a link prop's value). It
was keyed by the **target** uuid — the referenced instance's own uuid was
the row's primary key. That enforces "one target = one owner": a target
can only ever be referenced from a single owner. A second link to the
same target silently overwrites the first (`merge_link` is an
insert-or-replace keyed on the target).

This was a deliberate trade-off (see `file_values.py`: *"unlike
instance_values, whose target-uuid PK forbids multi-ref"*), and the
many-to-one escape hatch was `Array<T>` membership. But the receipts
model needs a genuine many-to-one **direct** link: `ReceiptItem.product`
points at a `Product`, and many `ReceiptItem`s — across many receipts —
reference the same product. `Product.price` is then the ADR-0020 backlink
projection of all those items. Array membership cannot express this: the
item already belongs to the receipt's `Array<ReceiptItem>`, and an
instance is a member of arrays, not a bare many-to-one ref.

A second latent bug shares the same root cause: re-pointing a ref (`obj.p
= other`) via `merge_link` never removed the old target row, so the old
keying left a stale duplicate `(owner, prop)` link.

## Decision

Re-key `instance_values` on `(inst_uuid, prop_uuid)` — "one target per
(owner, prop)", which is what a single-valued link prop already means —
and demote the target `uuid` to a plain, indexed foreign-key column.

- `uuid` (target) → `nullable=False`, `index=True`, still
  `ForeignKey("instances.uuid")`.
- `inst_uuid` + `prop_uuid` → composite primary key.
- `merge_link` keeps its body: `Database.merge` now keys by
  `(inst_uuid, prop_uuid)`, so re-pointing a ref correctly *replaces*
  the target in place (fixing the stale-duplicate bug as a side effect).
- `link_for(inst_uuid, prop_uuid)` is now unique by construction.
- Reverse lookups (`backlink_refs`, `delete_links_to`) query
  `WHERE uuid = target`, served by the new index.

Migration `schema/020_instance_values_many_to_one.sql` collapses any
stale `(owner, prop)` duplicates, re-keys the PK idempotently, and adds
the target index.

## Consequences

- **Positive:** direct refs are now true many-to-one; `product.price` =
  the full backlink set. Re-pointing a ref stops leaking stale links.
- **Negative:** the target column is no longer unique, so "which owners
  point here" is a full scan of `instance_values` filtered by `uuid` —
  but it already was (`backlink_refs`), just backed by an index now.
- `file_values` stays as-is; it already modelled the same `(owner, prop)`
  keying and was the reference for this change.
