# ADR-0026: Block-based formula editor (Scratch-like)

- **Status:** Accepted
- **Date:** 2026-09-16

## Context

Formulas (ADR-0005) are stored as text and today can only be written raw via
the API or the CLI — the v1 type editor ships "no formulas". The user wants to
compose formulas visually, Scratch-style, rather than type the DSL. The storage
format is not up for debate: a formula stays a single text string (ADR-0005),
because that string is what the validator, the rename-rewriter and the evaluator
all consume. A block editor is therefore a **pure UI layer** over the text:
blocks ⇄ AST ⇄ text.

We now have a conditional (ADR-0024) and aggregates (ADR-0023) in the DSL, so
the block editor must cover the full expression grammar, not just `SUM(...)`.

## Decision

### 1. The AST is the shared contract, serialized as a discriminated JSON union

The backend already owns the grammar and the AST (`nodes.py`). The frontend
must not re-implement the parser. Instead the AST is the contract between the
two, serialized as JSON keyed on `kind`:

```
{"kind": "number", "value": "2"}
{"kind": "ref", "key": "price"}
{"kind": "binop", "op": "*", "left": <node>, "right": <node>}
{"kind": "neg", "operand": <node>}
{"kind": "call", "func": "SUM", "path": ["lines", "price"]}
{"kind": "if", "prop": "kind", "op": "==", "value": "\"tax\"", "then": <node>, "else": <node>}
```

`Number.value` travels as a decimal string; `Call.path` is the `(array_key)`
or `(array_key, member_key)` tuple; `If.value` keeps the literal exactly as
written (quoted for string/enum, bare for numeric — ADR-0024).

### 2. Two stateless AST endpoints carry the transform

- `POST /api/formulas/parse` — body `{formula: str}` → `{ast: <node>}`. Raises
  422 on a syntax error, exactly like the save-path validator.
- `POST /api/formulas/render` — body `{ast: <node>}` → `{formula: str}`.
  Normalizes to canonical text via the existing `render`.

Both are pure conversions with no database read or write; the Python parser and
renderer remain the single source of truth. The frontend calls `parse` when it
opens a formula (text → blocks) and `render` when it commits an edit (blocks →
text). The canonical text is what gets saved through `syncProps` / `createType`
(already wired for `formula`/`collect`).

### 3. The editor is a click-to-compose block tree, not drag-and-drop

Scratch's value is the **nested block metaphor**, not the drag gesture. Drag is
a large, fiddly surface (drop targets, ghosting, touch). For v1 the editor
renders the AST as a nested tree of colored blocks with **slots**: click a slot
to open a palette and insert a block, click × to delete. Blocks:

| block | color | slots / fields |
|---|---|---|
| number | blue | decimal input |
| prop (Ref) | green | dropdown of sibling scalar prop keys |
| aggregate (Call) | purple | function dropdown (`SUM/AVERAGE/COUNT/MIN/MAX`) + array dropdown + member dropdown |
| operator (BinOp) | orange | operator dropdown (`+ - * /`) + two operand slots |
| negate (Neg) | orange | one operand slot |
| if (If) | yellow | cond prop dropdown + op dropdown (`==`/`!=`) + literal input + then/else slots |

The prop/array/member dropdowns are fed by the type's live schema (the same
data the editor already holds), so a block can never reference a nonexistent
key. The backend validator still runs on save and is the final gate.

### 4. `collect` stays a plain selector, not a block

A `collect` is a single member key on the element type of an `Array<T>` prop
(ADR-0025) — one dropdown, not an expression. It gets its own small editor in
the type editor next to the array prop's row, separate from the formula blocks.

## Consequences

- **Positive:** formulas become editable without typing the DSL; the AST
  contract keeps the parser single-sourced on the backend; `collect` is
  editable in the UI for the first time.
- **Negative:** two new endpoints and a block-editor surface add frontend
  complexity (the drag gesture is deliberately deferred). A future drag-and-drop
  is a gesture swap over the same AST tree, not a re-architecture.
- **Bounds:** the block editor edits *formula text* only. It does not invent new
  DSL features; whatever the grammar rejects is still rejected on save.
