# Prop-value tables: one mapped class per scalar/array/file value kind.
from nylium.tables.values.string_values import TABLE_StringValues
from nylium.tables.values.integer_values import TABLE_IntegerValues
from nylium.tables.values.numeric_values import TABLE_NumericValues
from nylium.tables.values.boolean_values import TABLE_BooleanValues
from nylium.tables.values.datetime_values import TABLE_DatetimeValues
from nylium.tables.values.date_values import TABLE_DateValues
from nylium.tables.values.time_values import TABLE_TimeValues
from nylium.tables.values.monthday_values import TABLE_MonthDayValues
from nylium.tables.values.monthdaytime_values import TABLE_MonthDayTimeValues
from nylium.tables.values.instance_values import TABLE_InstanceValues
from nylium.tables.values.array_values import TABLE_ArrayValues
from nylium.tables.values.file_values import TABLE_FileValues

__all__ = [
    "TABLE_StringValues",
    "TABLE_IntegerValues",
    "TABLE_NumericValues",
    "TABLE_BooleanValues",
    "TABLE_DatetimeValues",
    "TABLE_DateValues",
    "TABLE_TimeValues",
    "TABLE_MonthDayValues",
    "TABLE_MonthDayTimeValues",
    "TABLE_InstanceValues",
    "TABLE_ArrayValues",
    "TABLE_FileValues",
]
