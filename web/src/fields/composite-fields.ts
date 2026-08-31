/** Composite field kinds — link and array, peers of one file. */
import type { ArrayValue, ObjectView, PropValue, RefValue } from "../contracts";
import { PropValues, TypeNames } from "../contracts";
import { FieldFactory } from "./field-factory";
import { FieldModel } from "./field-model";

export class RefFieldModel extends FieldModel {
  /** Candidate objects of the link's target type — the editor store
   * fills this; the model itself never talks to the network. */
  options: readonly ObjectView[];
  selectedUuid: string | null;

  constructor(key: string, valueType: string, selectedUuid: string | null) {
    super(key, valueType);
    this.options = [];
    this.selectedUuid = selectedUuid;
  }

  static fromWire(key: string, valueType: string, value: PropValue | undefined): RefFieldModel {
    const selected =
      value !== undefined && PropValues.isRef(value) ? value.ref : null;
    return new RefFieldModel(key, valueType, selected?.uuid ?? null);
  }

  toWire(): RefValue {
    if (this.selectedUuid === null) {
      return { ref: null };
    }
    return { ref: { uuid: this.selectedUuid, type_name: this.valueType } };
  }
}

export class ArrayFieldModel extends FieldModel {
  items: FieldModel[];

  constructor(key: string, valueType: string, items: FieldModel[]) {
    super(key, valueType);
    this.items = items;
  }

  static fromWire(key: string, valueType: string, value: PropValue | undefined): ArrayFieldModel {
    const wireItems =
      value !== undefined && PropValues.isArray(value) && value.items !== null
        ? value.items
        : [];
    const elementType = TypeNames.elementOf(valueType);
    const items = wireItems.map((item) =>
      FieldFactory.createForType(key, elementType, item),
    );
    return new ArrayFieldModel(key, valueType, items);
  }

  get elementType(): string {
    return TypeNames.elementOf(this.valueType);
  }

  addItem(): FieldModel {
    const item = FieldFactory.createForType(this.key, this.elementType, undefined);
    this.items = [...this.items, item];
    return item;
  }

  removeItem(index: number): void {
    this.items = this.items.filter((_, position) => position !== index);
  }

  toWire(): ArrayValue {
    return { items: this.items.map((item) => item.toWire()) };
  }
}
