/** Wire contract mirroring nylium.api.views — keep the two in sync. */

export interface PropView {
  uuid: string;
  key: string;
  value_type: string;
}

export interface EnumOptionView {
  uuid: string;
  value: string;
}

export interface TypeView {
  name: string;
  /** null for builtins and array types — only user types carry both forms */
  plural_name: string | null;
  /** "object" (schema of props) or "enum" (list of string options) */
  kind: string;
  icon: string;
  color: string;
  props: PropView[];
  /** enum kinds only; always empty for object kinds */
  enum_options: EnumOptionView[];
}

export interface ObjectRef {
  uuid: string;
  type_name: string;
}

/** Decimal crosses the wire as a string (lossless), Datetime as ISO text. */
export type ScalarWire = string | number | boolean | null;

export interface ScalarValue {
  value: ScalarWire;
}

export interface RefValue {
  ref: ObjectRef | null;
}

export interface ArrayValue {
  items: PropValue[] | null;
}

export type PropValue = ScalarValue | RefValue | ArrayValue;

export interface ObjectView {
  uuid: string;
  type_name: string;
  props: Record<string, PropValue>;
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
  static readonly MONTH_DAY = "MonthDay";
  static readonly MONTH_DAY_TIME = "MonthDayTime";
  static readonly SCALARS: readonly string[] = [
    TypeNames.STRING,
    TypeNames.INTEGER,
    TypeNames.NUMERIC,
    TypeNames.BOOLEAN,
    TypeNames.DATETIME,
    TypeNames.DATE,
    TypeNames.TIME,
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
  private static readonly ARRAY_PREFIX = "Array<";

  static isScalar(name: string): boolean {
    return TypeNames.SCALARS.includes(name);
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

  /** Types a human edits in the sidebar — not builtins, not arrays. */
  static isUserType(name: string): boolean {
    return !TypeNames.isScalar(name) && !TypeNames.isArray(name);
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
