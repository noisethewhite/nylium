import type { PropValue, RefValue } from "../contracts";
import { PropValues } from "../contracts";
import { FieldModel } from "./field-model";

/** A File/Document/Image prop (ADR-0008): holds a `files.uuid` reference,
 * not an object link — files are first-class rows, not instances. The
 * wire shape still matches RefValue so the codec and API are unchanged. */
export class FileFieldModel extends FieldModel {
  selectedUuid: string | null;

  constructor(key: string, valueType: string, selectedUuid: string | null) {
    super(key, valueType);
    this.selectedUuid = selectedUuid;
  }

  static fromWire(key: string, valueType: string, value: PropValue | undefined): FileFieldModel {
    const selected = value !== undefined && PropValues.isRef(value) ? value.ref : null;
    return new FileFieldModel(key, valueType, selected?.uuid ?? null);
  }

  toWire(): RefValue {
    if (this.selectedUuid === null) {
      return { ref: null };
    }
    return { ref: { uuid: this.selectedUuid, type_name: this.valueType } };
  }
}
