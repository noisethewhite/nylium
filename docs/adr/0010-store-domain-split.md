# ADR-0010: Store/Domain split — a Mapping contract for table access and objects

- Status: accepted (2026-09-07)
- Date: 2026-09-07

## Context

nylium's data layer has no common shape. Every table class in `tables/` and
every domain object in `objects/` carries ad-hoc `classmethod`/`staticmethod`
helpers that were added as the code happened to need them, with no shared
contract. Three roles are fused into one class: a **row** (a SQLAlchemy
model), a **collection accessor** (query helpers), and a **domain service**
(validation/evaluation/parse logic). Nothing tells you what a class *is*
without reading every method.

The naming is the visible symptom. "Get by key" is spelled a dozen ways —
`by_uuid`, `by_name`, `by_hash`, `name_by_uuid`, `uuid_by_name`, `by_key`,
`by_class_name`, `by_type_name`, `by_credential_id`, `base_of`,
`get_type_name`, `type_uuid_of`, `name_of`. "List / count" is another dozen —
`all_uuids`, `list_all`, `all_names`, `list_for`, `values_of`, `names_of`,
`uuids_of_type`, `count_of_type`, `count_with_value_type`, `count_usage`,
`usage_count`, `usage_total`, `count_all`, `credential_ids_for`, `for_user`,
`instance_uuids`. `WFunction` mixes table access (`_nodes`, `_edges`) with the
evaluation algorithm (`_topo_sort`, `_eval_node`, `_assert_acyclic`);
`WType` mixes properties, static utilities (`array_name`, `function_params`)
and access (`by_name`, `ensure`).

Max wants this brought to a common denominator: dict-like interfaces
(`Types` as `dict[UUID, TypeRow]` / `dict[str, TypeRow]`, `WObject` as
`dict[str, PropValue]`), a few clean layers of abstraction with `get` /
`getattr`, so a product this important stays repairable.

## Decision

### 1. Three layers, one native protocol

Split the fused classes into three roles:

| Layer | What it is | Home |
|---|---|---|
| **Row** | thin SQLAlchemy model, columns only, no query helpers | `src/nylium/tables/` |
| **Store** | `Mapping[K, Row]` — collection access, one contract | `src/nylium/database/store.py` |
| **Domain** | object with semantics, but addressable as `Mapping[str, Value]` | `src/nylium/objects/` |

The common denominator is the native Python `Mapping` / `MutableMapping`
protocol — `__getitem__`, `get`, `__contains__`, `__iter__`, `__len__`,
`keys`/`values`/`items`, and `__setitem__`/`__delitem__` where mutable. No
bespoke per-class vocabulary; one way to read, one way to write, one way to
iterate.

### 2. Store — one generic access contract

A single `Store[K, V]` base provides the collection contract; thin
per-entity subclasses add indexes. `Types.name_by_uuid` becomes
`types[uuid].name`; `Types.all_names` becomes
`[t.name for t in types.values()]`; `uuid_by_name` becomes
`types.by_name(name)`. The ~40 "get by key" / "list count" helpers collapse
into the protocol.

A `Mapping` has one key type, so a second index (e.g. type name beside UUID)
is an explicit `by_name(...)` method or a second store, not an overloaded
`__getitem__`. Store reads are `@databasemethod(commit=False)`; writes are
`@databasemethod(commit=True)` and inherit the owner-commits-once semantics
already in place (ADR on transaction atomicity).

### 3. WObject becomes a MutableMapping

`WObject` already implements `__getattr__` / `__setattr__` / `__delattr__`.
It becomes an honest `MutableMapping[str, StoredValue]`:

```python
class WObject(MutableMapping[str, StoredValue]):
    def __getitem__(self, key): return self._read(key)
    def __setitem__(self, key, value): self._write(key, value)
    def __delitem__(self, key): self._clear(key)
    def __getattr__(self, key): return self[key]       # attribute access is an alias
    def __setattr__(self, key, value): self[key] = value
```

`get`, `in`, `len`, iteration and `items` come from the protocol. Attribute
access remains a convenience, but the single source of truth is `__getitem__`.

This also *fixes* a known collision class: a prop key that shadows a real
`WObject` method (`items`, `get`, `keys`) is unreachable through attribute
access but stays reachable through `obj["items"]`, because `__getitem__` does
not collide with methods.

### 4. Algorithms are services, not mappings

Not everything becomes a dict. `WFunction.evaluate`, `Formula.parse`,
`WUnit.validate`, `WEnum.validate` are **algorithms/services** — pure
functions with one input and one output, with no row access mixed in. Their
"common denominator" is a clear role (pure service), not `[]`. Forcing
`Mapping` onto them would invent a new kind of confusion. The domain/engine
split is: containers address by key, services compute.

### 5. Rollout in phases, not one diff

This is larger than one reviewable change, so it ships in phases, each a
separate tested diff:

1. `Store[K, V]` base + `TypeStore` pilot (the clearest offender).
2. Roll out to `InstanceStore`, `FileStore`, `PropStore`,
   `EnumOptionStore`, `UnitPartStore` and the value tables.
3. `WObject` → `MutableMapping` with attribute-access aliases.
4. Extract `WFunction`/`Formula`/`WUnit`/`WEnum` algorithm cores into pure
   services, leaving row access in stores.

Backward compatibility during rollout: existing helper methods stay as thin
delegates until their call sites migrate, then are removed. No half-migrated
state is committed.

## Consequences

- One way to read/write/iterate any table or object; a reader no longer
  needs to know per-class helper vocabulary.
- Fewer moving parts: ~40 helpers reduce to the `Mapping` protocol plus a
  handful of index methods.
- Repairability: a bug in "get by key" is fixed once in `Store`, not in
  every table's bespoke `*_by_*` method.
- `WObject` prop shadowing (`items`, `get`, `keys`) becomes addressable via
  `obj["items"]`.
- `WObject` now carries `MutableMapping` ABC requirements (`__getitem__`,
  `__setitem__`, `__delitem__`, `__iter__`, `__len__`) — the dynamic-access
  path must funnel through `__getitem__`/`__setitem__`, not bypass them.
- Temporary churn: helper delegates live until call sites migrate; the
  migration is bounded per phase.

## Rejected

- **Renaming helpers without separating layers.** Cosmetic; the three-role
  fusion and the ad-hoc vocabulary survive under a fresh coat of paint.
- **Making everything dict-like.** Stretches `Mapping` over pure algorithms
  (`evaluate`, `parse`, `validate`) where a key/iteration contract is
  meaningless.
- **Full Repository + Unit-of-Work pattern.** Overkill for a single-user
  typed object store; a `Store` Mapping with `@databasemethod` ownership is
  the right size. A heavier ORM-agnostic data layer buys nothing here.
- **Wrapping the ORM classes themselves as `Mapping`.** `Types[uuid]` on a
  SQLAlchemy model class collides with declarative machinery and mixes the
  row and collection roles again; the store is a separate object by design.

## LOC estimate

`Store[K, V]` base + `TypeStore` pilot ~100–150; rollout to remaining stores
~200–300; `WObject` → `MutableMapping` ~100–150; algorithm-service extraction
~150–200. Total well over the 250-LOC bar — ships in the phased diffs above,
each under the per-file budget.
