/** Wire contract mirroring nylium.api.views — keep the two in sync. */

export interface PropView {
  uuid: string;
  key: string;
  value_type: string;
  /** ADR-0005: a formula over the owner's Array<T> props, or null for a
   * plain stored prop */
  formula: string | null;
  /** ADR-0007: uuid of a Function<T,R> instance whose DAG computes this
   * prop on read, or null. Mutually exclusive with `formula`; like
   * formula-backed props it is read-only on the wire. */
  function_uuid: string | null;
}

export interface EnumOptionView {
  uuid: string;
  value: string;
}

/** One part of a user unit: the base part plus secondaries with an
 * affine factor (base = (entered - offset) / multiplier). Decimals
 * cross the wire as strings. */
export interface UnitPartView {
  uuid: string;
  name: string;
  multiplier: string;
  offset: string;
  is_base: boolean;
}

export interface TypeView {
  name: string;
  /** every type carries both forms, builtins included (ADR-0011 phase 8) */
  plural_name: string;
  /** "object" (schema of props), "enum" (list of options), "unit" (parts) */
  kind: string;
  icon: string;
  color: string;
  props: PropView[];
  /** enum kinds only; always empty for object kinds */
  enum_options: EnumOptionView[];
  /** unit kinds only; always empty for other kinds */
  unit_parts: UnitPartView[];
  /** ADR-0004: composition type — instances exist only as a prop value
   * of an owner object; no standalone creation, hidden from lists */
  embedded: boolean;
}

export interface ObjectRef {
  uuid: string;
  type_name: string;
}

/** Decimal crosses the wire as a string (lossless), Datetime as ISO text. */
export type ScalarWire = string | number | boolean | null;

export interface ScalarValue {
  value: ScalarWire;
  /** part name as entered for Numeric<Unit> props; null elsewhere */
  unit: string | null;
}

export interface RefValue {
  ref: ObjectRef | null;
}

export interface ArrayValue {
  items: PropValue[] | null;
}

/** ADR-0004: a composition child rendered inline. uuid null = never
 * filled (created lazily on first write). On input, props is the full
 * child draft; an empty props object clears the child. */
export interface EmbeddedValue {
  uuid: string | null;
  type_name: string;
  props: Record<string, PropValue>;
}

export type PropValue = ScalarValue | RefValue | ArrayValue | EmbeddedValue;

export interface ObjectView {
  uuid: string;
  type_name: string;
  props: Record<string, PropValue>;
  /** ADR-0005: derived tags — one per Array<T> edge pointing at this
   * object, colored by the owner type */
  tags: TagView[];
}

/** ADR-0008: a first-class file entity — a self-contained `files` row.
 * `uuid` is the stable pointer to the blob under FILES_DIR; `name` is a
 * renameable display name (no longer a stored scalar prop). */
export interface FileView {
  uuid: string;
  type_name: string;
  name: string;
  mime: string;
  size_bytes: number;
}

/** ADR-0005: one membership edge of an object, read-only projection. */
export interface TagView {
  owner_uuid: string;
  owner_name: string;
  prop_key: string;
  name: string;
  /** owner type's hex color (#RRGGBB) */
  color: string;
}

/** ADR-0007: one node of a function's action DAG. */
export interface FunctionNodeView {
  uuid: string;
  kind: string;
  position: number;
  config: Record<string, unknown>;
}

/** ADR-0007: one dataflow edge between two function nodes. */
export interface FunctionEdgeView {
  uuid: string;
  from_node_uuid: string;
  from_port: number;
  to_node_uuid: string;
  to_port: number;
}

/** ADR-0007: a Function<T,R> instance — parameterization, input link,
 * and the full action DAG. */
export interface FunctionView {
  uuid: string;
  name: string;
  type_name: string;
  input_type: string;
  output_type: string;
  input_object_uuid: string | null;
  nodes: FunctionNodeView[];
  edges: FunctionEdgeView[];
}

/** Wire draft of one node (client-generated uuid; config is scalar). */
export interface FunctionNodeInput {
  uuid: string;
  kind: string;
  position: number;
  config: Record<string, string | number>;
}

/** Wire draft of one edge (the server assigns the edge uuid). */
export interface FunctionEdgeInput {
  from_node_uuid: string;
  from_port: number;
  to_node_uuid: string;
  to_port: number;
}

/** Static helpers on the wire shapes — namespace-only, never instantiated. */
export abstract class PropValues {
  static isScalar(value: PropValue): value is ScalarValue {
    return "value" in value;
  }

  static isArray(value: PropValue): value is ArrayValue {
    return "items" in value;
  }

  static isRef(value: PropValue): value is RefValue {
    return "ref" in value;
  }

  static isEmbedded(value: PropValue): value is EmbeddedValue {
    return "type_name" in value;
  }
}

/** Type-name grammar of the backend — mirror of nylium.objects. */
export abstract class TypeNames {
  static readonly STRING = "String";
  static readonly INTEGER = "Integer";
  static readonly NUMERIC = "Numeric";
  static readonly BOOLEAN = "Boolean";
  static readonly DATETIME = "Datetime";
  static readonly DATE = "Date";
  static readonly TIME = "Time";
  static readonly COLOR = "Color";
  static readonly MONTH_DAY = "MonthDay";
  static readonly MONTH_DAY_TIME = "MonthDayTime";
  /** Blob-pointer builtins (ADR-0006): instances reference a file blob
   * under FILES_DIR keyed by instance uuid. */
  static readonly FILE = "File";
  static readonly DOCUMENT = "Document";
  static readonly IMAGE = "Image";
  static readonly FILES: readonly string[] = [
    TypeNames.FILE,
    TypeNames.DOCUMENT,
    TypeNames.IMAGE,
  ];
  static readonly SCALARS: readonly string[] = [
    TypeNames.STRING,
    TypeNames.INTEGER,
    TypeNames.NUMERIC,
    TypeNames.BOOLEAN,
    TypeNames.DATETIME,
    TypeNames.DATE,
    TypeNames.TIME,
    TypeNames.COLOR,
    TypeNames.MONTH_DAY,
    TypeNames.MONTH_DAY_TIME,
  ];
  /** The calendar family — the picker groups it under one submenu. */
  static readonly CALENDAR: readonly string[] = [
    TypeNames.TIME,
    TypeNames.DATE,
    TypeNames.DATETIME,
    TypeNames.MONTH_DAY,
    TypeNames.MONTH_DAY_TIME,
  ];
  /** The year-bearing date props the calendar grid places. MonthDay /
   * MonthDayTime have no year, so they can't anchor a month grid. */
  static readonly DATE_TYPES: readonly string[] = [
    TypeNames.DATE,
    TypeNames.DATETIME,
  ];
  private static readonly ARRAY_PREFIX = "Array<";
  private static readonly UNIT_NUMERIC_PREFIX = "Numeric<";
  private static readonly FUNCTION_PREFIX = "Function<";

  static isScalar(name: string): boolean {
    return TypeNames.SCALARS.includes(name);
  }

  static isDateType(name: string): boolean {
    return TypeNames.DATE_TYPES.includes(name);
  }

  static isFileType(name: string): boolean {
    return TypeNames.FILES.includes(name);
  }

  /** ADR-0007: parameterized function types — "Function<Invoice, Numeric>".
   * Never user-editable; they exist only as a function instance's type. */
  static isFunction(name: string): boolean {
    return name.startsWith(TypeNames.FUNCTION_PREFIX) && name.endsWith(">");
  }

  /** "Function<Invoice, Numeric>" -> { input: "Invoice", output: "Numeric" }. */
  static functionParams(name: string): { input: string; output: string } | null {
    if (!TypeNames.isFunction(name)) {
      return null;
    }
    const inner = name.slice(TypeNames.FUNCTION_PREFIX.length, -1);
    const comma = inner.indexOf(",");
    if (comma < 0) {
      return null;
    }
    return { input: inner.slice(0, comma).trim(), output: inner.slice(comma + 1).trim() };
  }

  /** ADR-0006: `img:<uuid>` type icons — blob of a live Image instance.
   * Contract-level so both the icon renderer and stores can parse it. */
  static readonly IMG_ICON_PREFIX = "img:";

  static imgIconUuid(icon: string): string | null {
    return icon.startsWith(TypeNames.IMG_ICON_PREFIX)
      ? icon.slice(TypeNames.IMG_ICON_PREFIX.length)
      : null;
  }

  static isArray(name: string): boolean {
    return name.startsWith(TypeNames.ARRAY_PREFIX) && name.endsWith(">");
  }

  static elementOf(name: string): string {
    return name.slice(TypeNames.ARRAY_PREFIX.length, -1);
  }

  static arrayOf(element: string): string {
    return `${TypeNames.ARRAY_PREFIX}${element}>`;
  }

  /** A numeric prop parameterized by a user unit: "Numeric<Temperature>". */
  static isUnitNumeric(name: string): boolean {
    return name.startsWith(TypeNames.UNIT_NUMERIC_PREFIX) && name.endsWith(">");
  }

  static unitParamOf(name: string): string | null {
    if (!TypeNames.isUnitNumeric(name)) {
      return null;
    }
    return name.slice(TypeNames.UNIT_NUMERIC_PREFIX.length, -1);
  }

  static unitNumericName(unit: string): string {
    return `${TypeNames.UNIT_NUMERIC_PREFIX}${unit}>`;
  }

  /** Types a human edits in the sidebar — not builtins, not arrays,
   * not parameterized forms like Numeric<Unit>, not Function<T,R>,
   * not the file kinds (File/Document/Image). */
  static isUserType(name: string): boolean {
    return (
      !TypeNames.isScalar(name) &&
      !TypeNames.isArray(name) &&
      !TypeNames.isUnitNumeric(name) &&
      !TypeNames.isFunction(name) &&
      !TypeNames.isFileType(name)
    );
  }
}

/** Human-facing labels for the calendar family — everything else
 * shows its raw type name. */
export const TypeLabels: Readonly<Record<string, string>> = {
  [TypeNames.TIME]: "Time",
  [TypeNames.DATE]: "Date",
  [TypeNames.DATETIME]: "Date & time",
  [TypeNames.MONTH_DAY]: "Date, no year",
  [TypeNames.MONTH_DAY_TIME]: "Date, no year & time",
};

/** Disk usage of the volume holding nylium's data (GET /api/storage). */
export interface StorageView {
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  /** database + blob store — nylium's own share of used_bytes */
  nylium_bytes: number;
}
