import type { PropValue, PropView } from "../contracts";
import { TypeNames } from "../contracts";
import { ArrayFieldModel, RefFieldModel } from "./composite-fields";
import { EnumFieldModel } from "./enum-fields";
import type { EnumOptionsOf } from "./enum-fields";
import { FieldModel } from "./field-model";
import {
  BooleanFieldModel,
  DateFieldModel,
  DatetimeFieldModel,
  DecimalFieldModel,
  IntegerFieldModel,
  MonthDayFieldModel,
  MonthDayTimeFieldModel,
  TextFieldModel,
  TimeFieldModel,
} from "./scalar-fields";

/** Declared type name -> the right FieldModel kind. The single place
 * that knows the whole hierarchy. `enumOptionsOf` resolves a type name
 * to its enum options; without it enum-typed props degrade to refs. */
export abstract class FieldFactory {
  static create(
    prop: PropView,
    value: PropValue | undefined,
    enumOptionsOf?: EnumOptionsOf,
  ): FieldModel {
    return FieldFactory.createForType(prop.key, prop.value_type, value, enumOptionsOf);
  }

  static createForType(
    key: string,
    valueType: string,
    value: PropValue | undefined,
    enumOptionsOf?: EnumOptionsOf,
  ): FieldModel {
    const enumOptions = enumOptionsOf?.(valueType) ?? null;
    if (enumOptions !== null) {
      return EnumFieldModel.fromWire(key, valueType, enumOptions, value);
    }
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
      case TypeNames.DATE:
        return DateFieldModel.fromWire(key, value);
      case TypeNames.TIME:
        return TimeFieldModel.fromWire(key, value);
      case TypeNames.MONTH_DAY:
        return MonthDayFieldModel.fromWire(key, value);
      case TypeNames.MONTH_DAY_TIME:
        return MonthDayTimeFieldModel.fromWire(key, value);
      default:
        if (TypeNames.isArray(valueType)) {
          return ArrayFieldModel.fromWire(key, valueType, value, enumOptionsOf);
        }
        return RefFieldModel.fromWire(key, valueType, value);
    }
  }
}
