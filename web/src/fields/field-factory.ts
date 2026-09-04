import type { PropValue, PropView } from "../contracts";
import { TypeNames } from "../contracts";
import { ArrayFieldModel, RefFieldModel } from "./composite-fields";
import type { EmbeddedSchemaOf } from "./embedded-fields";
import { EmbeddedFieldModel } from "./embedded-fields";
import { EnumFieldModel } from "./enum-fields";
import type { EnumOptionsOf } from "./enum-fields";
import { FieldModel } from "./field-model";
import type { UnitPartsOf } from "./unit-fields";
import { UnitDecimalFieldModel } from "./unit-fields";
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
 * that knows the whole hierarchy. `enumOptionsOf`/`unitPartsOf`
 * resolve a type name to its enum options / unit parts; without them
 * enum-typed props degrade to refs and Numeric<Unit> to plain decimal. */
export abstract class FieldFactory {
  static create(
    prop: PropView,
    value: PropValue | undefined,
    enumOptionsOf?: EnumOptionsOf,
    unitPartsOf?: UnitPartsOf,
    embeddedSchemaOf?: EmbeddedSchemaOf,
  ): FieldModel {
    return FieldFactory.createForType(
      prop.key,
      prop.value_type,
      value,
      enumOptionsOf,
      unitPartsOf,
      embeddedSchemaOf,
    );
  }

  static createForType(
    key: string,
    valueType: string,
    value: PropValue | undefined,
    enumOptionsOf?: EnumOptionsOf,
    unitPartsOf?: UnitPartsOf,
    embeddedSchemaOf?: EmbeddedSchemaOf,
  ): FieldModel {
    const enumOptions = enumOptionsOf?.(valueType) ?? null;
    if (enumOptions !== null) {
      return EnumFieldModel.fromWire(key, valueType, enumOptions, value);
    }
    const unitName = TypeNames.unitParamOf(valueType);
    if (unitName !== null) {
      const unit = unitPartsOf?.(unitName);
      if (unit !== null && unit !== undefined) {
        return UnitDecimalFieldModel.fromWire(
          key,
          valueType,
          unit.base,
          unit.parts,
          value,
        );
      }
      // unit type gone or not loaded yet — degrade to a plain decimal
      return DecimalFieldModel.fromWire(key, value);
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
          return ArrayFieldModel.fromWire(key, valueType, value, enumOptionsOf, unitPartsOf);
        }
        {
          const embeddedSchema = embeddedSchemaOf?.(valueType);
          if (embeddedSchema !== undefined && embeddedSchema.embedded) {
            return EmbeddedFieldModel.fromWire(
              key,
              valueType,
              embeddedSchema,
              value,
              enumOptionsOf,
              unitPartsOf,
              embeddedSchemaOf,
            );
          }
        }
        return RefFieldModel.fromWire(key, valueType, value);
    }
  }
}
