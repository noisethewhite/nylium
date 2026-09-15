# ADR-0021: Arrays of embedded instances (`Array<Embedded>`)

Status: proposed
Date: 2026-09-15

## Context

ADR-0004 (composition) deferred `Array<EmbeddedType>` to "phase 2". Real
models need it now: a `Receipt` owns an ordered list of `ReceiptItem`
children (each with `product`, `price`, `quantity`), and an ordered list
of `Fee` children. Today the only collection forms are `Array<Scalar>`
and `Array<StandaloneRef>` — the former boxes plain values, the latter
holds refs to already-existing objects. Neither can express "the parent
owns an ordered list of inline children, edited as a table".

The user wants `Receipt.items` (and `Receipt.fees`) to render as a
**table**: one embedded child per row, the child's own props as columns.

## Decisions

### Type-level: lift the ban

1. `Array<E>` is accepted where `E` is an embedded type. The guard in
   `ApiShared._ensure_value_type` (which raises "arrays of embedded type
   ... are not supported yet") is removed. `_normalize_value` already
   recurses into the element type and already turns an embedded-typed
   value into an inline props draft (ADR-0004 §"write side"), so no new
   normalization is needed — each element is a `dict[str, StoredValue]`.

### Ownership: the array owns its elements

2. An array element is an embedded child whose owner is the **array
   instance**, not the parent object:
   - `instances.owner_object_uuid = array_uuid`,
   - `instances.owner_prop_uuid = NULL`,
   - membership and order live in `array_values` (`array_uuid, index,
     value_uuid`) — the element has **no** `instance_values` link row.

   Rationale: the read-side index `owned_uuids(parent)` (used by
   `WObject.delete` for single embedded children) then never sees array
   elements, so a parent delete cascades through exactly one path —
   `WArray.destroy` → `_destroy_box` → child delete — with no
   double-delete. A single embedded child keeps its `instance_values`
   link; the presence of that link is what distinguishes the two cases.

3. Exclusive ownership is inherited: an embedded type already refuses
   out-of-owner references (`WTypeMeta.check_link`, ADR-0004 §4), and
   elements are created fresh, never linked from elsewhere.

### Names

4. An element's generated name is `<parent name> → <prop key> #<index>`
   (1-based). The `→` separator is already reserved (ADR-0004 §7);
   appending `#<index>` keeps sibling element names distinct. Names are
   written at array-write time and regenerated when the parent's name or
   the prop key changes (extending `WEmbedded.regenerate_names` to walk
   array props).

### Cascade lifecycle

5. Rewriting the array (`WArray._fill`) first destroys existing boxes;
   for an embedded element that means a full recursive delete of the
   child (its own embedded children and arrays) before the new elements
   are boxed. Deleting the parent, or deleting/clearing the array prop,
   reaches the same `WArray.destroy` path.

6. `sync_props` deleting or retyping an `Array<Embedded>` prop destroys
   its elements while the prop still stands (the array-prop analogue of
   `WEmbedded.destroy_children_of_prop`), so no embedded child orphanes.

### Read + UI

7. Reading an `Array<Embedded>` prop returns the wrapped child objects
   (existing `_unwrap` already wraps non-scalar elements). The frontend
   renders the array as a `<Table>` (the shared table primitive): one row
   per element, one column per prop of the embedded type, `remove` per
   row, and an add-row control. Editing an element edits its inline
   draft, saved with the parent in one transaction.

## Out of scope (phase 2)

- Drag-to-reorder UI (storage already carries `index`; reorder is a
  whole-array rewrite on the API side).
- Per-element inline nesting of further `Array<Embedded>` inside a
  table cell (works at the storage layer, deferred in the table UI).

## Consequences

- Storage model is unchanged: no new tables, no new columns — array
  elements reuse the existing `array_values` rows and the existing
  `owner_object_uuid` read-index, now pointing at the array instance.
- `WArray._box`/`_destroy_box` gain an embedded branch; `WEmbedded`
  gains an array-aware name path and name regeneration.
- The `Array<Embedded>` write path stays transactional and single-owner
  by construction, matching the rest of the composition model.
