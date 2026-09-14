import type {
  FunctionNodeInput,
  FunctionNodeView,
  TypeView,
} from "../contracts";
import { TypeNames } from "../contracts";

/** ADR-0007: a Function<T,R> is an action DAG of whitelisted nodes. This
 * module owns the closed node-kind set and the pure transformations over
 * node drafts — everything the form editor needs that is not JSX or a
 * React event binding. */

/** The closed set of node operations — frontend mirror of the backend's
 * WFunction.NODES whitelist (nylium/objects/wfunction.py, ADR-0007). */
export type NodeKind =
  | "get_prop"
  | "const"
  | "add"
  | "sub"
  | "mul"
  | "div"
  | "sum"
  | "average"
  | "count"
  | "min"
  | "max"
  | "cast"
  | "map";

type ConfigKey = "key" | "value" | "target" | null;

export interface KindSpec {
  arity: number;
  configKey: ConfigKey;
}

export interface NodeDraft {
  uuid: string;
  kind: NodeKind;
  config: Record<string, string | number>;
}

export interface EdgeDraft {
  from_node_uuid: string;
  to_node_uuid: string;
  to_port: number;
}

/** Mirror of WFunction.NODES (ADR-0007) — kind -> input arity + config
 * field. `Record<NodeKind, KindSpec>` forces the map to cover every kind
 * exactly once, so a missing or misspelled key is a compile error. */
export const KIND_SPECS: Record<NodeKind, KindSpec> = {
  get_prop: { arity: 0, configKey: "key" },
  const: { arity: 0, configKey: "value" },
  add: { arity: 2, configKey: null },
  sub: { arity: 2, configKey: null },
  mul: { arity: 2, configKey: null },
  div: { arity: 2, configKey: null },
  sum: { arity: 1, configKey: null },
  average: { arity: 1, configKey: null },
  count: { arity: 1, configKey: null },
  min: { arity: 1, configKey: null },
  max: { arity: 1, configKey: null },
  cast: { arity: 1, configKey: "target" },
  map: { arity: 1, configKey: "key" },
};

/** The node kinds in display order, derived from KIND_SPECS so the list
 * cannot drift from the specs. `Object.keys` is string-typed, but
 * KIND_SPECS is a complete `Record` over the closed NodeKind union, so
 * every runtime key is a NodeKind — the cast is safe. */
export const NODE_KINDS: readonly NodeKind[] = Object.keys(
  KIND_SPECS,
) as NodeKind[];

/** True when `kind` names a node the editor can render. `hasOwnProperty`
 * (not `in`) so inherited Object.prototype keys can't pass. */
export function isNodeKind(kind: string): kind is NodeKind {
  return Object.prototype.hasOwnProperty.call(KIND_SPECS, kind);
}

/** Namespace-only helper class for the function editor's node logic —
 * mirrors the `TypeNames` / `PropValues` / `ObjectLabels` convention. */
export abstract class FunctionEditorLogic {
  static newUuid(): string {
    return crypto.randomUUID();
  }

  static emptyConfig(key: ConfigKey): Record<string, string | number> {
    if (key === null) {
      return {};
    }
    return { [key]: "" };
  }

  static nodeLabel(node: NodeDraft): string {
    const spec = KIND_SPECS[node.kind];
    if (spec !== undefined && spec.configKey !== null) {
      const raw = node.config[spec.configKey];
      const text = raw === undefined || raw === "" ? "…" : String(raw);
      return `${node.kind} ${text}`;
    }
    return node.kind;
  }

  static toNodeInput(node: NodeDraft, position: number): FunctionNodeInput {
    return { uuid: node.uuid, kind: node.kind, position, config: node.config };
  }

  /** `const` values cross the wire typed: parse numerics, else keep text. */
  static parseConstValue(raw: string): string | number {
    const trimmed = raw.trim();
    if (trimmed === "") {
      return "";
    }
    const numeric = Number(trimmed);
    return Number.isNaN(numeric) ? raw : numeric;
  }

  /** Best-effort static output type of a node — a frontend mirror of
   * WFunction.node_output_type, just enough to resolve a `map` node's array
   * element type from its incoming edge. */
  static inferNodeType(
    node: NodeDraft,
    inputSchema: TypeView | undefined,
  ): string | undefined {
    if (node.kind === "get_prop") {
      return inputSchema?.props.find((prop) => prop.key === node.config.key)
        ?.value_type;
    }
    if (node.kind === "const") {
      return typeof node.config.value === "number"
        ? TypeNames.NUMERIC
        : typeof node.config.value === "string"
          ? TypeNames.STRING
          : undefined;
    }
    if (node.kind === "cast") {
      return typeof node.config.target === "string"
        ? node.config.target
        : undefined;
    }
    if (node.kind === "count") {
      return TypeNames.INTEGER;
    }
    if (
      node.kind === "sum" ||
      node.kind === "average" ||
      node.kind === "min" ||
      node.kind === "max" ||
      node.kind === "add" ||
      node.kind === "sub" ||
      node.kind === "mul" ||
      node.kind === "div"
    ) {
      return TypeNames.NUMERIC;
    }
    return undefined;
  }

  /** Wire boundary: narrow a `FunctionNodeView` (config: Record<string,
   * unknown>) into an editable `NodeDraft` (config: Record<string, string |
   * number>). Config entries that aren't string | number are dropped, never
   * silently retyped; a node whose kind this editor doesn't know yields
   * null so the caller filters it out. */
  static fromWireNode(node: FunctionNodeView): NodeDraft | null {
    if (!isNodeKind(node.kind)) {
      return null;
    }
    const config: Record<string, string | number> = {};
    for (const [key, value] of Object.entries(node.config)) {
      if (typeof value === "string" || typeof value === "number") {
        config[key] = value;
      }
    }
    return { uuid: node.uuid, kind: node.kind, config };
  }
}
