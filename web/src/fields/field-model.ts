import type { PropValue } from "../contracts";

/** Thrown by FieldModel.toWire when a draft can't become a valid
 * value of the declared type — caught by the editor, shown to the user. */
export class FieldValidationError extends Error {
  readonly fieldKey: string;

  constructor(fieldKey: string, detail: string) {
    super(`${fieldKey}: ${detail}`);
    this.name = "FieldValidationError";
    this.fieldKey = fieldKey;
  }
}

/** Base of the editor field hierarchy: one field = one prop draft.
 * Subclasses own the conversion between UI draft and wire PropValue. */
export abstract class FieldModel {
  readonly key: string;
  readonly valueType: string;

  protected constructor(key: string, valueType: string) {
    this.key = key;
    this.valueType = valueType;
  }

  abstract toWire(): PropValue;
}
