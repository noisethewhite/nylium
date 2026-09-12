/** Composite field kinds — link and array, peers of one file. */
import type { ArrayValue, ObjectView, PropValue, RefValue } from "../contracts";
import { PropValues, TypeNames } from "../contracts";
import type { EnumOptionsOf } from "./enum-fields";
import type { UnitPartsOf } from "./unit-fields";
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
    // the wire carries the selected object's concrete type name — for
    // Any<Trait> refs valueType is the bound spec, not a real type
    const selected = this.options.find((view) => view.uuid === this.selectedUuid);
    return {
      ref: { uuid: this.selectedUuid, type_name: selected?.type_name ?? this.valueType },
    };
  }
}

export class ArrayFieldModel extends FieldModel {
  items: FieldModel[];
  /** Carried so addItem builds the same item kinds fromWire did. */
  readonly enumOptionsOf: EnumOptionsOf | undefined;
  readonly unitPartsOf: UnitPartsOf | undefined;

  constructor(
    key: string,
    valueType: string,
    items: FieldModel[],
    enumOptionsOf?: EnumOptionsOf,
    unitPartsOf?: UnitPartsOf,
  ) {
    super(key, valueType);
    this.items = items;
    this.enumOptionsOf = enumOptionsOf;
    this.unitPartsOf = unitPartsOf;
  }

  static fromWire(
    key: string,
    valueType: string,
    value: PropValue | undefined,
    enumOptionsOf?: EnumOptionsOf,
    unitPartsOf?: UnitPartsOf,
  ): ArrayFieldModel {
    const wireItems =
      value !== undefined && PropValues.isArray(value) && value.items !== null
        ? value.items
        : [];
    const elementType = TypeNames.elementOf(valueType);
    const items = wireItems.map((item) =>
      FieldFactory.createForType(key, elementType, item, enumOptionsOf, unitPartsOf),
    );
    return new ArrayFieldModel(key, valueType, items, enumOptionsOf, unitPartsOf);
  }

  get elementType(): string {
    return TypeNames.elementOf(this.valueType);
  }

  addItem(): FieldModel {
    const item = FieldFactory.createForType(
      this.key,
      this.elementType,
      undefined,
      this.enumOptionsOf,
      this.unitPartsOf,
    );
    this.items = [...this.items, item];
    return item;
  }

  removeItem(index: number): void {
    this.items = this.items.filter((_, position) => position !== index);
  }

  /** First failing item wins — the plaque inside the array marks it. */
  override validationError(): string | null {
    for (const item of this.items) {
      const error = item.validationError();
      if (error !== null) {
        return error;
      }
    }
    return null;
  }

  toWire(): ArrayValue {
    return { items: this.items.map((item) => item.toWire()) };
  }
}
