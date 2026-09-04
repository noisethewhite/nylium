/** Wire contract mirroring nylium.api.views — keep the two in sync. */

export interface PropView {
  uuid: string;
  key: string;
  value_type: string;
  /** ADR-0005: a formula over the owner's Array<T> props, or null for a
   * plain stored prop */
  formula: string | null;
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
  /** null for builtins and array types — only user types carry both forms */
  plural_name: string | null;
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

/** ADR-0005: one membership edge of an object, read-only projection. */
export interface TagView {
  owner_uuid: string;
  owner_name: string;
  prop_key: string;
  name: string;
  /** owner type's hex color (#RRGGBB) */
  color: string;
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
  private static readonly ARRAY_PREFIX = "Array<";
  private static readonly UNIT_NUMERIC_PREFIX = "Numeric<";

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
   * not parameterized forms like Numeric<Unit>. */
  static isUserType(name: string): boolean {
    return (
      !TypeNames.isScalar(name) &&
      !TypeNames.isArray(name) &&
      !TypeNames.isUnitNumeric(name)
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
