# ADR-0007: Function<T, R> — computed scalar props from an action DAG

- Status: accepted
- Date: 2026-09-04

## Context

ADR-0005 gave props a `formula` string — a tiny arithmetic DSL over the
owner's `Array<T>` props, evaluated **lazily at read time** and never
stored. Formulas are useful but shallow: no branches, no string handling,
one input shape only, and the grammar is fixed code.

Max wants a general computation type instead: **`Function<T, R>`** — a
value that takes an object of type `T`, transforms it through a sequence
of **actions** (Apple-Shortcuts-style), and produces a scalar `R`. The
body is authored in a visual editor, not typed as source. A Python-code
block may come later as a separate step, but is out of scope now.

Hard requirements from the product side:

1. A function **is an object** (an instance), nameable and reusable. A
   prop of scalar type `R` can hold, instead of a stored `R`, a
   **reference to a function** whose output type is `R`.
2. The result is computed **lazily at read time** (exactly as ADR-0005
   formulas are) — the function's DAG is folded over its current input
   object whenever the prop is read, and nothing is materialized into
   the storage tables. There is no write-time recompute to maintain.
3. `R` is **strictly scalar** for this iteration (String, Integer,
   Numeric, Boolean, Date, Datetime, Time, MonthDay, MonthDayTime,
   Color). No object/array/unit outputs yet.
4. The input is a **reference to one whole object of type `T`**.
5. Cycle detection at **two levels**, both static (at save time, before
   any read-time recursion can loop): (a) a cycle *inside* one function's
   action graph, and (b) a cycle *across functions* (`a` feeds `b` feeds
   `c` feeds `a`).

## Decision

### Types

A new parameterized type name **`Function<T, R>`**, materialized as a
row in `types` with `kind = "function"` — the same pattern `Numeric<Unit>`
uses for its parameterized row. `T` is an object kind (the input), `R` is
a scalar. The parameterized row is created lazily by `ensure`, exactly as
`Numeric<Unit>` is.

The function type carries one pinned prop: **`input`**, typed `T` (a
link). It is the only prop; users cannot add props to a function type
(same restriction as other builtins). The action graph is **not** a
prop — it lives in dedicated tables keyed by the function *instance*
uuid, because each function instance has its own body.

### Action graph (DAG, not a linear chain)

The body is a directed acyclic graph of nodes. Decided with Max
(2026-09-04): build the graph schema now, not a linear chain — a linear
chain cannot express even "add two props" without a two-input node, and
that is already a branch.

```
function_nodes:  uuid PK, function_uuid → instances.uuid (CASCADE),
                 kind TEXT (whitelist below), position INT,
                 config JSON (per-kind params)
function_edges:  uuid PK, function_uuid → instances.uuid (CASCADE),
                 from_node_uuid → function_nodes.uuid (CASCADE),
                 from_port INT, to_node_uuid → function_nodes.uuid (CASCADE),
                 to_port INT
```

Every node has one output and zero-or-more inputs. Sources have no
inputs; the graph's **sink** (a distinguished node, `position`-first by
convention) is the function's output and must type to `R`. The function's
`input` link is the implicit root value every `get_prop` reads from.

**v1 node whitelist** (closed set, `kind` is validated against it; no
`eval`, no code execution — the RCE surface is structurally closed):

- `get_prop` — read a prop of the input object (config: prop key).
  Output type = that prop's type.
- `const` — a literal (config: value). Output type inferred from value.
- `add` / `sub` / `mul` / `div` — binary numeric ops (two inputs).
- `sum` / `average` / `count` / `min` / `max` — reductions over an
  `Array<T>` input (one input).
- `cast` — number↔string coercion (one input, config: target scalar).

No `if`/branching and no string formatting in v1 — next iteration.

### Static validation

At save time, the graph is validated before any row persists:

- **Topological sort** over `function_edges` — a back-edge (cycle inside
  the graph) is a 422.
- **Port arity + type conformance** — `add` takes exactly two numeric
  inputs; `sum` takes exactly one array; `get_prop`'s config key must be
  a real prop of `T`; `cast` targets a scalar. Type of the sink must
  equal `R`. Invalid → 422.

The same `wformula.py` numeric-type helpers are reused to answer "is this
type numeric / array".

### Evaluation

A pure interpreter walks the DAG in topo order. Each node reads its
input ports (already-computed values, memoized by node uuid) and returns
its output. No IO, no DB access inside a node — the input object is
materialized into a plain `Mapping[prop_key, StoredValue]` before
evaluation, so a node reads data, not the database. Div-by-zero and
missing/None inputs produce an empty result for that prop (mirrors the
ADR-0005 div-zero rule).

### Function as a prop value

`props` gains one nullable column **`function_uuid`** (FK → `instances.uuid`),
parallel to `formula`. A prop is exactly one of: stored, `formula` (lazy),
or `function` (lazy). `formula` and `function_uuid` are mutually exclusive
(422).

When a prop `P` of scalar type `R` is set to reference function `F`:

1. `F`'s output type must be `R` (422 otherwise).
2. On read, `F`'s DAG is folded over its `input` object and the result is
   returned in the object view (`PropView`), mirroring the `_eval_formula`
   path. Nothing is written to the storage tables; a div-by-zero or a
   missing input object renders an empty value.

Writes to a `function`-backed prop are refused (read-only), exactly as
formula props already are.

### Function dependency tracking

Because evaluation is lazy, there is no reactive recompute to maintain —
the cost is paid on read, not write (the mirror of ADR-0005). The
**`function_deps`** table still records each function's input object:

```
function_deps:  function_uuid → instances.uuid (PK),
                input_object_uuid → instances.uuid
```

but its only purpose now is to build the static cross-function graph for
cycle detection (next section). It is synced whenever a function's `input`
link changes. No ORM mutation listeners are needed.

### Cross-function cycle detection

At save time, `function_deps` is treated as a directed graph (function →
its input object; and an object → the functions that compute *its* props,
via `props.function_uuid`). A DFS (white/gray/black) detects a back-edge —
`a` computes `b`, `b` computes `c`, `c` computes `a` — and refuses the
write with a 422 naming the cycle. This is the guard against infinite
read-time recursion when function-backed props chain through one another.

## Consequences

- New `kind = "function"` — the type-system ladder gets a fourth kind;
  `types.kind` is a free TEXT column so no migration, but every switch
  over `kind` (create-type validation, list filtering, icon/color
  defaults) must learn it.
- New tables `function_nodes`, `function_edges`, `function_deps` plus
  `props.function_uuid` — schema additions in `_ensure_schema` (idempotent
  ALTER for the new column, as with ADR-0006).
- Lazy evaluation means compute cost is paid on read, not write — the same
  tradeoff as formulas. A function-backed prop is cheap to bind and always
  fresh, but every object read that carries it folds the DAG once.
- The `eval`-free DAG keeps the RCE surface closed by construction; when a
  Python-code block is added later it must bring its own sandbox and is a
  separate ADR.

## Rejected

- **Extend the ADR-0005 formula grammar** — formulas are lazy, arithmetic-
  only, and read a fixed array shape; functions are a different value
  model (eager, reusable object, arbitrary input object).
- **Body as a linear step chain first** — cannot express "add two props"
  without a two-input node; the graph schema is built now so no migration
  when branching is needed.
- **Python source as the body (this iteration)** — reintroduces the
  arbitrary-code execution surface the whitelist closes; deferred to its
  own sandboxed ADR.
- **Eager reactive recompute (ORM mutation listeners + cascade)** — the
  original plan; abandoned for lazy read-time evaluation. It paid
  complexity up front (root resolution, topological cascade, event
  ordering) for a benefit the lazy path gets for free: freshness without
  invalidation.
