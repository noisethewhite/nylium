"""Canonical value-type names (the ``TYPE_NAME`` of each scalar wrapper).

A shared leaf so both the objects layer (``wscalar``) and the tables layer
(``tables.values`` stores) can reference these names without importing each
other. Importing ``wscalar`` from a value store would close a cycle:
``wscalar`` -> ``tables.values`` -> stores -> ``wscalar`` (ADR-0031).
"""

STRING = "String"
INTEGER = "Integer"
NUMERIC = "Numeric"
BOOLEAN = "Boolean"
DATETIME = "Datetime"
DATE = "Date"
TIME = "Time"
COLOR = "Color"
MONTH_DAY = "MonthDay"
MONTH_DAY_TIME = "MonthDayTime"
