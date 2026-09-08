# Domain-object tables: the type registry, instances and their props, plus
# the parameter tables for enum and unit types (ADR-0011).
from nylium.tables.objects.typeref import TABLE_Types
from nylium.tables.objects.props import TABLE_Props, Prop, Props, props
from nylium.tables.objects.enum_options import (
    TABLE_EnumOptions,
    EnumOption,
    EnumOptions,
    enum_options,
)
from nylium.tables.objects.unit_parts import (
    TABLE_UnitParts,
    UnitPart,
    UnitParts,
    unit_parts,
)
from nylium.tables.objects.types import Type, Types, types
from nylium.tables.objects.instances import (
    TABLE_Instances,
    Instance,
    Instances,
    instances,
    unique_plural_name,
)

__all__ = [
    "TABLE_Types",
    "TABLE_Props",
    "TABLE_EnumOptions",
    "TABLE_UnitParts",
    "TABLE_Instances",
    "Type",
    "Types",
    "types",
    "Prop",
    "Props",
    "props",
    "EnumOption",
    "EnumOptions",
    "enum_options",
    "UnitPart",
    "UnitParts",
    "unit_parts",
    "Instance",
    "Instances",
    "instances",
    "unique_plural_name",
]
