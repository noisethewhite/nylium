import type { ReactElement } from "react";
import { useMemo, useState } from "react";
import type {
  FunctionEdgeInput,
  FunctionNodeInput,
  PropView,
  TypeView,
} from "../contracts";
import { TypeNames } from "../contracts";
import { useObservable } from "../state/use-observable";
import { usePinTabOnEdit } from "../state/use-pin-tab-on-edit";
import { WorkspaceStore } from "../state/workspace";
import { ObjectLabels } from "./object-labels";
import { TypeIcon } from "./type-icon";
import { TypeSelect } from "./type-select";

/** ADR-0007: a Function<T,R> is an action DAG of whitelisted nodes. The
 * editor is form-based — nodes and edges as rows — because the closed
 * v1 node set (get_prop/const/arithmetic/aggregates/cast) is small enough
 * that a canvas would be ceremony, not power. */

interface NodeDraft {
  uuid: string;
  kind: string;
  config: Record<string, string | number>;
}

interface EdgeDraft {
  from_node_uuid: string;
  to_node_uuid: string;
  to_port: number;
}

type ConfigKey = "key" | "value" | "target" | null;

interface KindSpec {
  arity: number;
  configKey: ConfigKey;
}

/** Mirror of WFunction.NODES — kind -> input arity + config field. */
const KIND_SPECS: Record<string, KindSpec> = {
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

const NODE_KINDS = Object.keys(KIND_SPECS);

function newUuid(): string {
  return crypto.randomUUID();
}

function emptyConfig(key: ConfigKey): Record<string, string | number> {
  if (key === null) {
    return {};
  }
  return { [key]: "" };
}

function nodeLabel(node: NodeDraft): string {
  const spec = KIND_SPECS[node.kind];
  if (spec?.configKey !== null && spec !== undefined) {
    const raw = node.config[spec.configKey];
    const text = raw === undefined || raw === "" ? "…" : String(raw);
    return `${node.kind} ${text}`;
  }
  return node.kind;
}

function toNodeInput(node: NodeDraft, position: number): FunctionNodeInput {
  return { uuid: node.uuid, kind: node.kind, position, config: node.config };
}

/** `const` values cross the wire typed: parse numerics, else keep text. */
function parseConstValue(raw: string): string | number {
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
function inferNodeType(
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

export function FunctionEditor(props: {
  workspace: WorkspaceStore;
  uuid?: string;
}): ReactElement {
  const state = useObservable(props.workspace);
  const existing = props.uuid === undefined
    ? undefined
    : state.functions.find((view) => view.uuid === props.uuid);

  const [name, setName] = useState(existing?.name ?? "");
  const [inputType, setInputType] = useState(
    existing?.input_type ?? "",
  );
  const [outputType, setOutputType] = useState(
    existing?.output_type ?? TypeNames.NUMERIC,
  );
  const [inputObjectUuid, setInputObjectUuid] = useState<string | null>(
    existing?.input_object_uuid ?? null,
  );
  const [nodes, setNodes] = useState<NodeDraft[]>(
    existing?.nodes.map((node) => ({
      uuid: node.uuid,
      kind: node.kind,
      config: Object.fromEntries(
        Object.entries(node.config).map(([key, value]) => [
          key,
          value as string | number,
        ]),
      ),
    })) ?? [],
  );
  const [edges, setEdges] = useState<EdgeDraft[]>(
    existing?.edges.map((edge) => ({
      from_node_uuid: edge.from_node_uuid,
      to_node_uuid: edge.to_node_uuid,
      to_port: edge.to_port,
    })) ?? [],
  );

  const inputTypes = state.types.filter(
    (view) => view.kind === "object" && !view.embedded,
  );
  const inputSchema = state.types.find((view) => view.name === inputType);
  const inputObjects = state.objects.filter(
    (view) => view.type_name === inputType,
  );
  // get_prop reads scalar or array props only
  const readableProps =
    inputSchema === undefined
      ? []
      : inputSchema.props.filter(
          (prop) =>
            TypeNames.isScalar(prop.value_type) ||
            TypeNames.isArray(prop.value_type),
        );

  // `map` reads one prop off each element of its incoming array — resolve
  // the element type from the node feeding the map, then expose its props.
  const mapElementProps = (node: NodeDraft): PropView[] => {
    const incoming = edges.filter(
      (edge) => edge.to_node_uuid === node.uuid && edge.to_port === 0,
    );
    const fromUuid = incoming[0]?.from_node_uuid;
    if (incoming.length !== 1 || fromUuid === undefined) {
      return [];
    }
    const source = nodes.find((n) => n.uuid === fromUuid);
    if (source === undefined) {
      return [];
    }
    const sourceType = inferNodeType(source, inputSchema);
    if (sourceType === undefined || !TypeNames.isArray(sourceType)) {
      return [];
    }
    const elementName = TypeNames.elementOf(sourceType);
    const elementSchema = state.types.find((view) => view.name === elementName);
    if (elementSchema === undefined) {
      return [];
    }
    return elementSchema.props.filter(
      (prop) =>
        TypeNames.isScalar(prop.value_type) ||
        TypeNames.isArray(prop.value_type),
    );
  };

  const addNode = (kind: string): void => {
    const spec = KIND_SPECS[kind];
    if (spec === undefined) {
      return;
    }
    setNodes([
      ...nodes,
      { uuid: newUuid(), kind, config: emptyConfig(spec.configKey) },
    ]);
  };

  const setNodeKind = (uuid: string, kind: string): void => {
    const spec = KIND_SPECS[kind];
    if (spec === undefined) {
      return;
    }
    setNodes(
      nodes.map((node) =>
        node.uuid === uuid
          ? { uuid, kind, config: emptyConfig(spec.configKey) }
          : node,
      ),
    );
  };

  const setNodeConfig = (
    uuid: string,
    key: string,
    value: string | number,
  ): void => {
    setNodes(
      nodes.map((node) =>
        node.uuid === uuid
          ? { ...node, config: { ...node.config, [key]: value } }
          : node,
      ),
    );
  };

  const removeNode = (uuid: string): void => {
    setNodes(nodes.filter((node) => node.uuid !== uuid));
    setEdges(
      edges.filter(
        (edge) =>
          edge.from_node_uuid !== uuid && edge.to_node_uuid !== uuid,
      ),
    );
  };

  const addEdge = (): void => {
    setEdges([...edges, { from_node_uuid: "", to_node_uuid: "", to_port: 0 }]);
  };

  const setEdge = (
    index: number,
    patch: Partial<EdgeDraft>,
  ): void => {
    setEdges(
      edges.map((edge, i) => (i === index ? { ...edge, ...patch } : edge)),
    );
  };

  const removeEdge = (index: number): void => {
    setEdges(edges.filter((_, i) => i !== index));
  };

  const wireNodes = useMemo(
    () => nodes.map((node, index) => toNodeInput(node, index)),
    [nodes],
  );
  const wireEdges = useMemo<FunctionEdgeInput[]>(
    () =>
      edges
        .filter(
          (edge) => edge.from_node_uuid !== "" && edge.to_node_uuid !== "",
        )
        .map((edge) => ({
          from_node_uuid: edge.from_node_uuid,
          from_port: 0,
          to_node_uuid: edge.to_node_uuid,
          to_port: edge.to_port,
        })),
    [edges],
  );

  const pristine =
    existing === undefined ||
    (name === existing.name &&
      inputType === existing.input_type &&
      outputType === existing.output_type &&
      inputObjectUuid === existing.input_object_uuid &&
      JSON.stringify(wireNodes) === JSON.stringify(existing.nodes) &&
      JSON.stringify(wireEdges) === JSON.stringify(existing.edges));
  usePinTabOnEdit(props.workspace, !pristine);

  const canSave = name.trim() !== "" && inputType !== "" && outputType !== "";

  const save = (): void => {
    if (!canSave) {
      return;
    }
    if (props.uuid === undefined) {
      void props.workspace.createFunction(
        inputType,
        outputType,
        name.trim(),
        inputObjectUuid,
        wireNodes,
        wireEdges,
      );
    } else {
      void props.workspace.saveFunctionEdits(
        props.uuid,
        name.trim(),
        inputObjectUuid,
        wireNodes,
        wireEdges,
      );
    }
  };

  return (
    <div className="function-editor">
      <div className="function-editor-head">
        <input
          className="input function-name-input"
          placeholder="Function name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <button
          className="button button-primary"
          disabled={!canSave}
          onClick={save}
        >
          {props.uuid === undefined ? "Create" : "Save"}
        </button>
        {props.uuid !== undefined && (
          <button
            className="button button-danger"
            onClick={() => void props.workspace.deleteFunction(props.uuid as string)}
          >
            Delete
          </button>
        )}
      </div>

      <div className="function-editor-meta">
        <label className="field">
          <span className="field-label">Input type</span>
          <span className="field-body">
            <TypeSelect
              workspace={props.workspace}
              value={inputType}
              options={inputTypes.map((view) => view.name)}
              onChange={(value) => {
                setInputType(value);
                setInputObjectUuid(null);
              }}
              emptyLabel="— object type —"
              placeholder="Search object types…"
            />
          </span>
        </label>
        <label className="field">
          <span className="field-label">Output type</span>
          <span className="field-body">
            <TypeSelect
              workspace={props.workspace}
              value={outputType}
              options={TypeNames.SCALARS}
              onChange={setOutputType}
              placeholder="Search scalars…"
            />
          </span>
        </label>
        <label className="field">
          <span className="field-label">Input object</span>
          <span className="field-body">
            <select
              className="input"
              value={inputObjectUuid ?? ""}
              onChange={(event) =>
                setInputObjectUuid(event.target.value === "" ? null : event.target.value)
              }
            >
              <option value="">— none (compose on read) —</option>
              {inputObjects.map((object) => (
                <option key={object.uuid} value={object.uuid}>
                  {ObjectLabels.of(object)}
                </option>
              ))}
            </select>
          </span>
        </label>
      </div>

      <div className="function-editor-section">
        <div className="function-editor-section-head">
          <span className="dim">Nodes</span>
          <select
            className="input function-add-select"
            value=""
            onChange={(event) => {
              if (event.target.value !== "") {
                addNode(event.target.value);
              }
            }}
          >
            <option value="">+ add node</option>
            {NODE_KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </select>
        </div>
        {nodes.length === 0 && (
          <div className="empty-state dim">No nodes yet — add one below.</div>
        )}
        {nodes.map((node) => (
          <div className="function-node-row" key={node.uuid}>
            <select
              className="input function-node-kind"
              value={node.kind}
              onChange={(event) => setNodeKind(node.uuid, event.target.value)}
            >
              {NODE_KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {kind}
                </option>
              ))}
            </select>
            {node.kind === "get_prop" && (
              <select
                className="input function-node-config"
                value={String(node.config.key ?? "")}
                onChange={(event) =>
                  setNodeConfig(node.uuid, "key", event.target.value)
                }
              >
                <option value="">— prop —</option>
                {readableProps.map((prop) => (
                  <option key={prop.key} value={prop.key}>
                    {prop.key} ({prop.value_type})
                  </option>
                ))}
              </select>
            )}
            {node.kind === "map" && (
              <select
                className="input function-node-config"
                value={String(node.config.key ?? "")}
                onChange={(event) =>
                  setNodeConfig(node.uuid, "key", event.target.value)
                }
              >
                <option value="">— element prop —</option>
                {mapElementProps(node).map((prop) => (
                  <option key={prop.key} value={prop.key}>
                    {prop.key} ({prop.value_type})
                  </option>
                ))}
              </select>
            )}
            {node.kind === "const" && (
              <input
                className="input function-node-config"
                placeholder="value"
                value={String(node.config.value ?? "")}
                onChange={(event) =>
                  setNodeConfig(node.uuid, "value", event.target.value)
                }
                onBlur={(event) => {
                  const parsed = parseConstValue(event.target.value);
                  if (parsed !== event.target.value) {
                    setNodeConfig(node.uuid, "value", parsed);
                  }
                }}
              />
            )}
            {node.kind === "cast" && (
              <TypeSelect
                workspace={props.workspace}
                value={String(node.config.target ?? "")}
                options={TypeNames.SCALARS}
                onChange={(value) => setNodeConfig(node.uuid, "target", value)}
                placeholder="Search scalars…"
                triggerClassName="input type-picker-trigger function-node-config"
              />
            )}
            <button
              className="icon-button"
              title="Remove node"
              onClick={() => removeNode(node.uuid)}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      <div className="function-editor-section">
        <div className="function-editor-section-head">
          <span className="dim">Edges</span>
          <button className="button" onClick={addEdge}>
            + add edge
          </button>
        </div>
        {edges.length === 0 && (
          <div className="empty-state dim">
            No edges. Leaf nodes (get_prop, const) need none.
          </div>
        )}
        {edges.map((edge, index) => (
          <div className="function-edge-row" key={index}>
            <select
              className="input function-edge-from"
              value={edge.from_node_uuid}
              onChange={(event) =>
                setEdge(index, { from_node_uuid: event.target.value })
              }
            >
              <option value="">— from —</option>
              {nodes.map((node) => (
                <option key={node.uuid} value={node.uuid}>
                  {nodeLabel(node)}
                </option>
              ))}
            </select>
            <span className="dim">→</span>
            <select
              className="input function-edge-to"
              value={edge.to_node_uuid}
              onChange={(event) =>
                setEdge(index, { to_node_uuid: event.target.value })
              }
            >
              <option value="">— to —</option>
              {nodes.map((node) => (
                <option key={node.uuid} value={node.uuid}>
                  {nodeLabel(node)}
                </option>
              ))}
            </select>
            <input
              className="input function-edge-port"
              type="number"
              min={0}
              max={2}
              value={edge.to_port}
              onChange={(event) =>
                setEdge(index, { to_port: Number(event.target.value) || 0 })
              }
              title="to port (0=left/unary, 1=right operand)"
            />
            <button
              className="icon-button"
              title="Remove edge"
              onClick={() => removeEdge(index)}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {existing !== undefined && (
        <div className="function-editor-summary dim">
          <TypeIcon icon="functions" color="gray" size={14} />{" "}
          {existing.type_name}
        </div>
      )}
    </div>
  );
}
