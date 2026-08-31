/** Scalar field kinds — peers mirroring the backend's closed scalar
 * world (WString/WInteger/WNumeric/WBoolean/WDatetime), hence one file. */
import type { PropValue, ScalarValue } from "../contracts";
import { PropValues, TypeNames } from "../contracts";
import { FieldModel, FieldValidationError } from "./field-model";

export abstract class ScalarFieldModel extends FieldModel {
  draft: string;

  protected constructor(key: string, valueType: string, draft: string) {
    super(key, valueType);
    this.draft = draft;
  }

  protected static scalarDraft(value: PropValue | undefined): string {
    if (value !== undefined && PropValues.isScalar(value) && value.value !== null) {
      return String(value.value);
    }
    return "";
  }

  protected emptyAsNull(): ScalarValue | null {
    return this.draft === "" ? { value: null } : null;
  }
}

export class TextFieldModel extends ScalarFieldModel {
  static fromWire(key: string, value: PropValue | undefined): TextFieldModel {
    return new TextFieldModel(key, TypeNames.STRING, ScalarFieldModel.scalarDraft(value));
  }

  toWire(): ScalarValue {
    return { value: this.draft === "" ? null : this.draft };
  }
}

export class IntegerFieldModel extends ScalarFieldModel {
  private static readonly PATTERN = /^-?\d+$/;

  static fromWire(key: string, value: PropValue | undefined): IntegerFieldModel {
    return new IntegerFieldModel(key, TypeNames.INTEGER, ScalarFieldModel.scalarDraft(value));
  }

  toWire(): ScalarValue {
    const empty = this.emptyAsNull();
    if (empty !== null) {
      return empty;
    }
    if (!IntegerFieldModel.PATTERN.test(this.draft)) {
      throw new FieldValidationError(this.key, "integer expected");
    }
    return { value: Number.parseInt(this.draft, 10) };
  }
}

export class DecimalFieldModel extends ScalarFieldModel {
  static fromWire(key: string, value: PropValue | undefined): DecimalFieldModel {
    return new DecimalFieldModel(key, TypeNames.NUMERIC, ScalarFieldModel.scalarDraft(value));
  }

  toWire(): ScalarValue {
    const empty = this.emptyAsNull();
    if (empty !== null) {
      return empty;
    }
    const parsed = Number(this.draft);
    if (!Number.isFinite(parsed)) {
      throw new FieldValidationError(this.key, "number expected");
    }
    // the draft string itself crosses the wire — the backend parses it
    // into Decimal losslessly, no binary float detour
    return { value: this.draft };
  }
}

export class BooleanFieldModel extends FieldModel {
  checked: boolean;

  constructor(key: string, checked: boolean) {
    super(key, TypeNames.BOOLEAN);
    this.checked = checked;
  }

  static fromWire(key: string, value: PropValue | undefined): BooleanFieldModel {
    const checked =
      value !== undefined && PropValues.isScalar(value) && value.value === true;
    return new BooleanFieldModel(key, checked);
  }

  toWire(): ScalarValue {
    return { value: this.checked };
  }
}

export class DatetimeFieldModel extends ScalarFieldModel {
  /** datetime-local inputs want "YYYY-MM-DDTHH:mm" — the first 16
   * chars of an ISO stamp. */
  private static readonly LOCAL_LENGTH = 16;

  static fromWire(key: string, value: PropValue | undefined): DatetimeFieldModel {
    return new DatetimeFieldModel(
      key,
      TypeNames.DATETIME,
      ScalarFieldModel.scalarDraft(value).slice(0, DatetimeFieldModel.LOCAL_LENGTH),
    );
  }

  toWire(): ScalarValue {
    // the backend parses ISO via datetime.fromisoformat
    return { value: this.draft === "" ? null : this.draft };
  }
}
