import type { ReactElement } from "react";
import { useEffect, useState } from "react";
import type { FormulaNode, TypeView } from "../contracts";
import { TypeNames } from "../contracts";

/** The closed reduction set — mirror of wformula.nodes.FUNCTIONS. */
const FUNCS = ["SUM", "AVERAGE", "COUNT", "MIN", "MAX"] as const;
const OPS = ["+", "-", "*", "/"] as const;
const CMP_OPS = ["==", "!="] as const;

/** Locally re-render an AST to formula text (mirrors the backend `render`).
 * `if.value` is stored raw (no quotes); it is quoted here so the emitted
 * text matches the DSL's `IF(prop op "lit", …)` shape. */
function astToText(node: FormulaNode): string {
  switch (node.kind) {
    case "number":
      return node.value;
    case "ref":
      return node.key;
    case "neg":
      return `-${astToText(node.operand)}`;
    case "binop":
      return `(${astToText(node.left)} ${node.op} ${astToText(node.right)})`;
    case "call":
      return `${node.func}(${node.path.join(".")})`;
    case "if":
      return `IF(${node.prop} ${node.op} "${node.value}", ${astToText(node.then)}, ${astToText(node.else)})`;
  }
}

/** Unquote a backend `if.value` (the wire keeps the literal exactly as
 * written — quoted for a string/enum) back to the raw editor value. */
function unquoteIfValue(ast: FormulaNode): FormulaNode {
  switch (ast.kind) {
    case "if": {
      const raw =
        ast.value.length >= 2 && ast.value.startsWith('"') && ast.value.endsWith('"')
          ? ast.value.slice(1, -1)
          : ast.value;
      return { ...ast, value: raw, then: unquoteIfValue(ast.then), else: unquoteIfValue(ast.else) };
    }
    case "binop":
      return { ...ast, left: unquoteIfValue(ast.left), right: unquoteIfValue(ast.right) };
    case "neg":
      return { ...ast, operand: unquoteIfValue(ast.operand) };
    default:
      return ast;
  }
}

/** The live schema facts the block editor offers in its dropdowns. */
interface BlockContext {
  /** numeric sibling prop keys — the `Ref` targets */
  refProps: string[];
  /** String/enum sibling prop keys — the `IF` cond targets */
  stringProps: string[];
  /** array prop keys with the element type's member keys — `Call` targets */
  arrayProps: { key: string; members: string[] }[];
}

function contextOf(schema: TypeView, types: readonly TypeView[]): BlockContext {
  const enumNames = new Set(types.filter((t) => t.kind === "enum").map((t) => t.name));
  const numeric = new Set([TypeNames.INTEGER, TypeNames.NUMERIC]);
  const refProps = schema.props
    .filter((p) => numeric.has(p.value_type) || TypeNames.isUnitNumeric(p.value_type))
    .map((p) => p.key);
  const stringProps = schema.props
    .filter((p) => p.value_type === TypeNames.STRING || enumNames.has(p.value_type))
    .map((p) => p.key);
  const arrayProps = schema.props
    .filter((p) => TypeNames.isArray(p.value_type))
    .map((p) => {
      const element = TypeNames.elementOf(p.value_type);
      const members = types.find((t) => t.name === element)?.props.map((m) => m.key) ?? [];
      return { key: p.key, members };
    });
  return { refProps, stringProps, arrayProps };
}

function membersOf(ctx: BlockContext, arrayKey: string): string[] {
  return ctx.arrayProps.find((a) => a.key === arrayKey)?.members ?? [];
}

/** One immutable slot: the nested operand of a binop/neg/if. A slot is
 * always filled (deleting replaces it with a zero number). */
function Slot(props: {
  node: FormulaNode;
  onChange: (next: FormulaNode) => void;
  ctx: BlockContext;
}): ReactElement {
  return (
    <span className="block-slot">
      <NodeBlock node={props.node} onChange={props.onChange} ctx={props.ctx} />
    </span>
  );
}

/** Render one AST node as a colored block with inline editors. */
function NodeBlock(props: {
  node: FormulaNode;
  onChange: (next: FormulaNode) => void;
  ctx: BlockContext;
}): ReactElement {
  const { node, onChange, ctx } = props;
  switch (node.kind) {
    case "number":
      return (
        <span className="block block-number">
          <input
            className="block-number-input"
            value={node.value}
            onChange={(e) => onChange({ ...node, value: e.target.value })}
          />
        </span>
      );
    case "ref":
      return (
        <span className="block block-ref">
          <select
            className="block-select"
            value={node.key}
            onChange={(e) => onChange({ ...node, key: e.target.value })}
          >
            {ctx.refProps.map((key) => (
              <option key={key} value={key}>
                {key}
              </option>
            ))}
          </select>
        </span>
      );
    case "call":
      return (
        <span className="block block-call">
          <select
            className="block-select"
            value={node.func}
            onChange={(e) => onChange({ ...node, func: e.target.value })}
          >
            {FUNCS.map((func) => (
              <option key={func} value={func}>
                {func}
              </option>
            ))}
          </select>
          <select
            className="block-select"
            value={node.path[0] ?? ""}
            onChange={(e) => onChange({ ...node, path: [e.target.value] })}
          >
            {ctx.arrayProps.map((a) => (
              <option key={a.key} value={a.key}>
                {a.key}
              </option>
            ))}
          </select>
          {node.func !== "COUNT" && node.path[0] !== undefined && (
            <select
              className="block-select"
              value={node.path[1] ?? ""}
              onChange={(e) => onChange({ ...node, path: [node.path[0] ?? "", e.target.value] })}
            >
              {membersOf(ctx, node.path[0]).map((member) => (
                <option key={member} value={member}>
                  .{member}
                </option>
              ))}
            </select>
          )}
        </span>
      );
    case "binop":
      return (
        <span className="block block-binop">
          <Slot node={node.left} onChange={(left) => onChange({ ...node, left })} ctx={ctx} />
          <select
            className="block-select block-op"
            value={node.op}
            onChange={(e) => onChange({ ...node, op: e.target.value })}
          >
            {OPS.map((op) => (
              <option key={op} value={op}>
                {op}
              </option>
            ))}
          </select>
          <Slot node={node.right} onChange={(right) => onChange({ ...node, right })} ctx={ctx} />
        </span>
      );
    case "neg":
      return (
        <span className="block block-neg">
          <span className="block-neg-sign">−</span>
          <Slot node={node.operand} onChange={(operand) => onChange({ ...node, operand })} ctx={ctx} />
        </span>
      );
    case "if":
      return (
        <span className="block block-if">
          <span className="block-if-label">IF</span>
          <select
            className="block-select"
            value={node.prop}
            onChange={(e) => onChange({ ...node, prop: e.target.value })}
          >
            {ctx.stringProps.map((key) => (
              <option key={key} value={key}>
                {key}
              </option>
            ))}
          </select>
          <select
            className="block-select block-op"
            value={node.op}
            onChange={(e) => onChange({ ...node, op: e.target.value })}
          >
            {CMP_OPS.map((op) => (
              <option key={op} value={op}>
                {op}
              </option>
            ))}
          </select>
          <input
            className="block-number-input"
            value={node.value}
            placeholder="value"
            onChange={(e) => onChange({ ...node, value: e.target.value })}
          />
          <span className="block-if-branch">then</span>
          <Slot node={node.then} onChange={(then) => onChange({ ...node, then })} ctx={ctx} />
          <span className="block-if-branch">else</span>
          <Slot node={node.else} onChange={(els) => onChange({ ...node, else: els })} ctx={ctx} />
        </span>
      );
  }
}

/** ADR-0026: compose a formula as nested colored blocks. Owns the AST —
 * parses the stored text on open, re-renders text on every edit. */
export function FormulaBlockEditor(props: {
  formula: string | null;
  onChange: (formula: string | null) => void;
  schema: TypeView;
  types: readonly TypeView[];
  parse: (formula: string) => Promise<FormulaNode>;
}): ReactElement {
  const { formula, onChange, schema, types, parse } = props;
  const [node, setNode] = useState<FormulaNode | null>(null);
  const [loaded, setLoaded] = useState(false);
  const ctx = contextOf(schema, types);

  useEffect(() => {
    let alive = true;
    setLoaded(false);
    if (!formula) {
      setNode(null);
      setLoaded(true);
      return;
    }
    parse(formula)
      .then((ast) => {
        if (alive) setNode(unquoteIfValue(ast));
      })
      .catch(() => {
        if (alive) setNode(null);
      })
      .finally(() => {
        if (alive) setLoaded(true);
      });
    return () => {
      alive = false;
    };
  }, [formula, parse]);

  const commit = (next: FormulaNode | null): void => {
    setNode(next);
    onChange(next ? astToText(next) : null);
  };

  const insert = (block: FormulaNode): void => commit(block);
  const zero: FormulaNode = { kind: "number", value: "0" };

  return (
    <div className="formula-block-editor">
      <div className="formula-palette">
        <button className="palette-item palette-number" onClick={() => insert(zero)}>
          Number
        </button>
        <button
          className="palette-item palette-ref"
          disabled={ctx.refProps.length === 0}
          onClick={() => insert({ kind: "ref", key: ctx.refProps[0] ?? "" })}
        >
          Variable
        </button>
        <button
          className="palette-item palette-call"
          disabled={ctx.arrayProps.length === 0}
          onClick={() => insert({ kind: "call", func: "SUM", path: [ctx.arrayProps[0]?.key ?? ""] })}
        >
          Aggregate
        </button>
        <button
          className="palette-item palette-binop"
          onClick={() => insert({ kind: "binop", op: "+", left: zero, right: zero })}
        >
          Operator
        </button>
        <button
          className="palette-item palette-if"
          disabled={ctx.stringProps.length === 0}
          onClick={() =>
            insert({
              kind: "if",
              prop: ctx.stringProps[0] ?? "",
              op: "==",
              value: "",
              then: zero,
              else: zero,
            })
          }
        >
          If
        </button>
      </div>
      <div className="formula-canvas">
        {!loaded ? (
          <span className="dim">…</span>
        ) : node === null ? (
          <span className="dim">Empty — pick a block above</span>
        ) : (
          <div className="formula-canvas-tree">
            <NodeBlock node={node} onChange={commit} ctx={ctx} />
            <button className="button" onClick={() => commit(null)}>
              Clear
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/** ADR-0026: a right-hand side panel hosting the block editor. The editor
 * lives in a drawer instead of an inline popover so a nested formula has
 * room to breathe; it closes on Escape, the × button, or the backdrop. */
export function FormulaDrawer(props: {
  open: boolean;
  onClose: () => void;
  title: string;
  formula: string | null;
  onChange: (formula: string | null) => void;
  schema: TypeView;
  types: readonly TypeView[];
  parse: (formula: string) => Promise<FormulaNode>;
}): ReactElement | null {
  const { open, onClose } = props;
  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);
  if (!open) {
    return null;
  }
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer formula-drawer">
        <header className="drawer-header">
          <span className="drawer-title">{props.title}</span>
          <button className="icon-button" title="Close" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="drawer-body">
          <FormulaBlockEditor
            formula={props.formula}
            onChange={props.onChange}
            schema={props.schema}
            types={props.types}
            parse={props.parse}
          />
        </div>
      </aside>
    </>
  );
}
