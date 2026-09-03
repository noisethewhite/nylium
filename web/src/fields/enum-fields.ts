import type { PropValue, ScalarValue } from "../contracts";
import { PropValues } from "../contracts";
import { FieldModel, FieldValidationError } from "./field-model";

/** Resolves a declared type name to its enum options, or null when
 * the type isn't an enum — the workspace builds it, the fields layer
 * never sees the store. */
export type EnumOptionsOf = (typeName: string) => readonly string[] | null;

/** Draft of an enum prop: one of the option strings or null (unset).
 * The wire shape is a plain ScalarValue — enums are strings under the
 * hood, membership is checked against the option snapshot. */
export class EnumFieldModel extends FieldModel {
  readonly options: readonly string[];
  selected: string | null;

  constructor(
    key: string,
    valueType: string,
    options: readonly string[],
    selected: string | null,
  ) {
    super(key, valueType);
    this.options = options;
    this.selected = selected;
  }

  static fromWire(
    key: string,
    valueType: string,
    options: readonly string[],
    value: PropValue | undefined,
  ): EnumFieldModel {
    const selected =
      value !== undefined && PropValues.isScalar(value) && typeof value.value === "string"
        ? value.value
        : null;
    return new EnumFieldModel(key, valueType, options, selected);
  }

  override validationError(): string | null {
    if (this.selected !== null && !this.options.includes(this.selected)) {
      return `${JSON.stringify(this.selected)} is not an option`;
    }
    return null;
  }

  toWire(): ScalarValue {
    if (this.selected !== null && !this.options.includes(this.selected)) {
      throw new FieldValidationError(
        this.key,
        `${JSON.stringify(this.selected)} is not an option`,
      );
    }
    return { value: this.selected };
  }
}
