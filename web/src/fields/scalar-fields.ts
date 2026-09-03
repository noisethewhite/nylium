/** Scalar field kinds — peers mirroring the backend's closed scalar
 * world (WString/WInteger/WNumeric/WBoolean and the calendar family
 * WDatetime/WDate/WTime/WMonthDay/WMonthDayTime), hence one file. */
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

  /** Regex a non-empty draft must match; null = free text. */
  protected pattern(): RegExp | null {
    return null;
  }

  /** Message shown on the red plaque when the draft breaks the pattern. */
  protected hint(): string {
    return "invalid format";
  }

  override validationError(): string | null {
    if (this.draft === "") {
      return null;
    }
    const pattern = this.pattern();
    if (pattern === null || pattern.test(this.draft)) {
      return null;
    }
    return this.hint();
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

  protected override pattern(): RegExp {
    return IntegerFieldModel.PATTERN;
  }

  protected override hint(): string {
    return "integer expected";
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
  private static readonly PATTERN = /^-?\d+(\.\d+)?$/;

  static fromWire(key: string, value: PropValue | undefined): DecimalFieldModel {
    return new DecimalFieldModel(key, TypeNames.NUMERIC, ScalarFieldModel.scalarDraft(value));
  }

  protected override pattern(): RegExp {
    return DecimalFieldModel.PATTERN;
  }

  protected override hint(): string {
    return "number expected";
  }

  toWire(): ScalarValue {
    const empty = this.emptyAsNull();
    if (empty !== null) {
      return empty;
    }
    if (!DecimalFieldModel.PATTERN.test(this.draft)) {
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
  private static readonly PATTERN = /^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d$/;

  static fromWire(key: string, value: PropValue | undefined): DatetimeFieldModel {
    return new DatetimeFieldModel(
      key,
      TypeNames.DATETIME,
      ScalarFieldModel.scalarDraft(value).slice(0, DatetimeFieldModel.LOCAL_LENGTH),
    );
  }

  protected override pattern(): RegExp {
    return DatetimeFieldModel.PATTERN;
  }

  protected override hint(): string {
    return "YYYY-MM-DDTHH:MM expected";
  }

  toWire(): ScalarValue {
    // the backend parses ISO via datetime.fromisoformat
    return { value: this.draft === "" ? null : this.draft };
  }
}

export class DateFieldModel extends ScalarFieldModel {
  /** date inputs want "YYYY-MM-DD" — the first 10 chars. */
  private static readonly LOCAL_LENGTH = 10;
  private static readonly PATTERN = /^\d{4}-\d{2}-\d{2}$/;

  static fromWire(key: string, value: PropValue | undefined): DateFieldModel {
    return new DateFieldModel(
      key,
      TypeNames.DATE,
      ScalarFieldModel.scalarDraft(value).slice(0, DateFieldModel.LOCAL_LENGTH),
    );
  }

  protected override pattern(): RegExp {
    return DateFieldModel.PATTERN;
  }

  protected override hint(): string {
    return 'e.g. "August 8, 1995"';
  }

  toWire(): ScalarValue {
    return { value: this.draft === "" ? null : this.draft };
  }
}

export class TimeFieldModel extends ScalarFieldModel {
  /** time inputs want "HH:mm" — the first 5 chars. */
  private static readonly LOCAL_LENGTH = 5;
  private static readonly PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

  static fromWire(key: string, value: PropValue | undefined): TimeFieldModel {
    return new TimeFieldModel(
      key,
      TypeNames.TIME,
      ScalarFieldModel.scalarDraft(value).slice(0, TimeFieldModel.LOCAL_LENGTH),
    );
  }

  protected override pattern(): RegExp {
    return TimeFieldModel.PATTERN;
  }

  protected override hint(): string {
    return "HH:MM expected";
  }

  toWire(): ScalarValue {
    return { value: this.draft === "" ? null : this.draft };
  }
}

/** Year-less dates: draft is the backend stamp "MM-DD". The UI edits it
 * through month/day selects, the regex still guards the raw draft — a
 * partial selection ("05-") fails it and shows the plaque. */
export class MonthDayFieldModel extends ScalarFieldModel {
  private static readonly PATTERN = /^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;

  static fromWire(key: string, value: PropValue | undefined): MonthDayFieldModel {
    return new MonthDayFieldModel(key, TypeNames.MONTH_DAY, ScalarFieldModel.scalarDraft(value));
  }

  protected override pattern(): RegExp {
    return MonthDayFieldModel.PATTERN;
  }

  protected override hint(): string {
    return "month and day both expected";
  }

  toWire(): ScalarValue {
    const empty = this.emptyAsNull();
    if (empty !== null) {
      return empty;
    }
    if (!MonthDayFieldModel.PATTERN.test(this.draft)) {
      throw new FieldValidationError(this.key, "month and day both expected");
    }
    return { value: this.draft };
  }
}

export class MonthDayTimeFieldModel extends ScalarFieldModel {
  private static readonly PATTERN = /^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T([01]\d|2[0-3]):[0-5]\d$/;

  static fromWire(key: string, value: PropValue | undefined): MonthDayTimeFieldModel {
    return new MonthDayTimeFieldModel(key, TypeNames.MONTH_DAY_TIME, ScalarFieldModel.scalarDraft(value));
  }

  protected override pattern(): RegExp {
    return MonthDayTimeFieldModel.PATTERN;
  }

  protected override hint(): string {
    return "month, day and time all expected";
  }

  toWire(): ScalarValue {
    const empty = this.emptyAsNull();
    if (empty !== null) {
      return empty;
    }
    if (!MonthDayTimeFieldModel.PATTERN.test(this.draft)) {
      throw new FieldValidationError(this.key, "month, day and time all expected");
    }
    return { value: this.draft };
  }
}
