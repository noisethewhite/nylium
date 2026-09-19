# ADR-0029: Instance-bound functions reading sibling props

- Status: proposed
- Date: 2026-09-18

## Context

ADR-0007 made a function an object — `Function<T,R>` — with a pinned
`input` prop (a link to one whole object of type `T`) and a type-level
binding: `props.function_uuid` marks a prop so that **every instance of
that type** renders the function's output in place of the prop's stored
value. Evaluation is lazy at read time; a function can read another
function's output (composition) by recursing through `materialize_input`.

Two things about that model no longer match how Max actually uses it:

1. **The input is the wrong thing.** A real formula-shaped need is
   "`Receipt.total = SUM(lines.line_total)`" — fold over the *receipt's
   own* props, not over a separate pinned input object. The pinned
   `input` link forces the author to point the function at one
   hand-picked object instead of the object the function is attached to.

2. **The binding is on the wrong level.** `props.function_uuid` binds a
   function to a *type*, so one function body serves every instance. Max
   wants to insert a function into a *specific object*, in place of a
   specific prop's value, the same way a prop otherwise stores a scalar.
   Different instances of one type may bind different functions (or
   none).

Max's requirement, verbatim: functions insert into an **object**, not a
type; they insert in place of a prop value whose type equals the
function's return type; they change their return value as soon as one of
their input values changes; and if several functions are chained, the
whole chain re-evaluates.

## Decision

### Function `T` is the owner type, not an input object

`Function<T,R>` keeps its parameterized shape, but `T` now names the
**owner** — the type of the object the function will be inserted into —
not a separate input object. The function no longer carries a pinned
`input` link. `get_prop` reads a sibling prop of the owner.

A function is reusable across every instance of `T`: `get_prop` resolves
against whichever object the function is currently bound into. The DAG,
the node whitelist, the static type rules and the evaluation interpreter
are unchanged — only what `get_prop` reads from changes.

### Instance-level binding replaces `props.function_uuid`

A new table records, per (instance, prop), which function computes that
prop:

```
instance_function_links:
  inst_uuid      → instances.uuid  (PK, CASCADE)
  prop_uuid      → props.uuid      (PK, CASCADE)
  function_uuid  → instances.uuid
```

This is the function analogue of `instance_values` (which stores link
targets). The type-level `props.function_uuid` column is dropped: the
only consumer is the type binding being replaced, and prod currently has
zero functions, so the migration is empty. Binding a function to an
instance prop is validated exactly as the old type binding was:

- `function.output_type == prop.value_type` (else 422);
- the prop is not `formula`-backed, not `collect`, not trait-bound.

### Evaluation reads the owner, not an input object

`materialize_input(function_uuid)` becomes `materialize_owner(inst_uuid)`:
project the owner's sibling props to `prop-key → value`, resolving a
sibling that is itself function-backed recursively (the composition that
already exists). `ObjectView._eval_function` passes the owner instance in
so the function folds over the object it is attached to.

The read-time lazy model is unchanged — "changes its return value when
an input changes" is what lazy read-time evaluation already guarantees,
and the chain recompute ("several functions chained") is the existing
recursive composition, now sourced from the owner. No write-time
recompute, no ORM mutation listeners (this was rejected in ADR-0007 and
the reasoning holds).

### Cycle detection becomes local

Cross-function cycle detection (`assert_no_dependency_cycle`) currently
builds a global function→input-object graph. With owner-sourced inputs
that graph collapses to: *within one owner*, function `A` (bound to prop
`P`) reads a sibling prop `Q` that is itself computed by function `B`
(bound to `Q`), and so on. A cycle is therefore local to a single owner's
prop graph. The same white/gray/black DFS runs, but scoped per owner,
when a function is bound or its DAG is saved.

## Consequences

- New table `instance_function_links`; dropped column
  `props.function_uuid` (empty migration — prod has no functions).
- `FunctionView` drops `input_object_uuid`; gains nothing — `T` already
  names the owner via `input_type`.
- `FunctionsApi.create_function` / `update_function` lose the
  `input_object_uuid` argument; a new `set_instance_prop_function` (or an
  object-scoped variant of `set_prop_function`) binds per instance.
- `WFunction.inputs` re-targets from a pinned input object to an owner
  instance; `function_deps` (the input-object index) is removed.
- Frontend: `FunctionBindButton` moves out of the type editor into the
  object editor — bind a function to a specific instance's prop instead
  of to the schema. The DAG editor is unchanged; its `get_prop` picker
  now lists the owner type's props (it already lists `input_type`'s).
- The already-merged display fix (re-derive `computed` on save) is the
  frontend half of "return value changes when an input changes" — lazy
  eval computes it, the editor now re-renders it.

## Rejected

- **Keep `props.function_uuid` and add instance-level as an override.**
  Two binding levels for one concept, and the type-level path still
  carries the pinned-input semantics Max is moving away from. Prod has no
  functions, so there is nothing to preserve.
- **Keep the pinned `input` object and just re-bind per instance.** The
  pinned input is precisely what makes `total = SUM(lines…)` awkward —
  the author should not have to point at an object the function is
  already attached to.
- **Eager reactive recompute.** Rejected in ADR-0007; lazy read-time
  evaluation plus the display fix already delivers observable
  reactivity without an invalidation system to maintain.
