import type { PropValue, PropView } from "../contracts";
import { TypeNames } from "../contracts";
import { ArrayFieldModel, RefFieldModel } from "./composite-fields";
import { FieldModel } from "./field-model";
import {
  BooleanFieldModel,
  DatetimeFieldModel,
  DecimalFieldModel,
  IntegerFieldModel,
  TextFieldModel,
} from "./scalar-fields";

/** Declared type name -> the right FieldModel kind. The single place
 * that knows the whole hierarchy. */
export abstract class FieldFactory {
  static create(prop: PropView, value: PropValue | undefined): FieldModel {
    return FieldFactory.createForType(prop.key, prop.value_type, value);
  }

  static createForType(
    key: string,
    valueType: string,
    value: PropValue | undefined,
  ): FieldModel {
    switch (valueType) {
      case TypeNames.STRING:
        return TextFieldModel.fromWire(key, value);
      case TypeNames.INTEGER:
        return IntegerFieldModel.fromWire(key, value);
      case TypeNames.NUMERIC:
        return DecimalFieldModel.fromWire(key, value);
      case TypeNames.BOOLEAN:
        return BooleanFieldModel.fromWire(key, value);
      case TypeNames.DATETIME:
        return DatetimeFieldModel.fromWire(key, value);
      default:
        if (TypeNames.isArray(valueType)) {
          return ArrayFieldModel.fromWire(key, valueType, value);
        }
        return RefFieldModel.fromWire(key, valueType, value);
    }
  }
}
