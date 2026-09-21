"""Object tables — mapped Rows + their stores, one file per table (ADR-0033)."""
from nylium.table_rows.objects.enum_option import EnumOption, EnumOptions, enum_options
from nylium.table_rows.objects.instance import Instance, Instances, instances
from nylium.table_rows.objects.prop import Prop, Props, SchemaItem, props
from nylium.table_rows.objects.trait import Trait, Traits, traits
from nylium.table_rows.objects.type import Type, Types, types
from nylium.table_rows.objects.type_trait import TypeTrait, TypeTraits, type_traits
from nylium.table_rows.objects.unit_part import UnitPart, UnitParts, unit_parts

__all__ = [
    "EnumOption",
    "EnumOptions",
    "Instance",
    "Instances",
    "Prop",
    "Props",
    "SchemaItem",
    "Trait",
    "Traits",
    "Type",
    "Types",
    "TypeTrait",
    "TypeTraits",
    "UnitPart",
    "UnitParts",
    "enum_options",
    "instances",
    "props",
    "traits",
    "types",
    "type_traits",
    "unit_parts",
]
