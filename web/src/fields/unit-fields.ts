import type { PropValue, ScalarValue } from "../contracts";
import { PropValues } from "../contracts";
import { FieldValidationError } from "./field-model";
import { ScalarFieldModel } from "./scalar-fields";

/** Resolves a unit type name to its parts — the base name for display,
 * plus every valid label. The workspace builds it; the fields layer
 * never sees the store. */
export type UnitPartsOf = (
  unitTypeName: string,
) => { readonly base: string; readonly parts: readonly string[] } | null;

/** Draft of a Numeric<Unit> prop: a decimal draft plus the part the
 * number is entered in. null unit = the base part (the canonical
 * storage form) — the picker shows the base name for it. The wire
 * shape is a ScalarValue with a unit label; membership and conversion
 * are checked server-side, the model only guards obvious breakage.
 * Extends ScalarFieldModel directly rather than DecimalFieldModel:
 * its fromWire needs the extra parts/base parameters, which would
 * break the static-side inheritance check. */
export class UnitDecimalFieldModel extends ScalarFieldModel {
  private static readonly PATTERN = /^-?\d+(\.\d+)?$/;

  readonly base: string;
  readonly parts: readonly string[];
  unit: string | null;

  constructor(
    key: string,
    valueType: string,
    draft: string,
    base: string,
    parts: readonly string[],
    unit: string | null,
  ) {
    super(key, valueType, draft);
    this.base = base;
    this.parts = parts;
    this.unit = unit;
  }

  static fromWire(
    key: string,
    valueType: string,
    base: string,
    parts: readonly string[],
    value: PropValue | undefined,
  ): UnitDecimalFieldModel {
    const draft =
      value !== undefined && PropValues.isScalar(value) && value.value !== null
        ? String(value.value)
        : "";
    const unit =
      value !== undefined && PropValues.isScalar(value) ? value.unit : null;
    return new UnitDecimalFieldModel(key, valueType, draft, base, parts, unit);
  }

  protected override pattern(): RegExp {
    return UnitDecimalFieldModel.PATTERN;
  }

  protected override hint(): string {
    return "number expected";
  }

  override validationError(): string | null {
    const numericError = super.validationError();
    if (numericError !== null) {
      return numericError;
    }
    if (this.unit !== null && !this.parts.includes(this.unit)) {
      return `${JSON.stringify(this.unit)} is not a part of this unit`;
    }
    return null;
  }

  override toWire(): ScalarValue {
    if (this.draft === "") {
      // clearing the value also clears the part label
      return { value: null, unit: null };
    }
    if (!UnitDecimalFieldModel.PATTERN.test(this.draft)) {
      throw new FieldValidationError(this.key, "number expected");
    }
    if (this.unit !== null && !this.parts.includes(this.unit)) {
      throw new FieldValidationError(
        this.key,
        `${JSON.stringify(this.unit)} is not a part of this unit`,
      );
    }
    // the draft string itself crosses the wire — the backend parses it
    // into Decimal losslessly and converts into the base part
    return { value: this.draft, unit: this.unit };
  }
}
