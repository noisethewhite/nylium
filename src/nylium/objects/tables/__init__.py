"""Mapped domain-object tables and their Table stores.

The persistence half of the domain-object split (ADR-0019): raw
SQLAlchemy ``TABLE_*`` classes (``table_<name>.py``) and the Table
mapping + singleton stores (``<name>s.py``) live here. The Row snapshots
they map onto live in ``nylium.objects.rows``.

Import order below is load-bearing: each module is imported only after
its dependencies (types last, after enum_options/unit_parts it renders).
"""
from nylium.objects.tables.table_types import TABLE_Types
from nylium.objects.tables.props import TABLE_Props, Prop, Props, props
from nylium.objects.tables.traits import (
    TABLE_Traits,
    TABLE_TypeTraits,
    Trait,
    Traits,
    TypeTrait,
    TypeTraits,
    traits,
    type_traits,
)
from nylium.objects.tables.enum_options import (
    TABLE_EnumOptions,
    EnumOption,
    EnumOptions,
    enum_options,
)
from nylium.objects.tables.unit_parts import (
    TABLE_UnitParts,
    UnitPart,
    UnitParts,
    unit_parts,
)
from nylium.objects.tables.types import Type, Types, types
from nylium.objects.tables.instances import (
    TABLE_Instances,
    Instance,
    Instances,
    instances,
    unique_plural_name,
)

__all__ = [
    "TABLE_Types",
    "TABLE_Props",
    "TABLE_Traits",
    "TABLE_TypeTraits",
    "TABLE_EnumOptions",
    "TABLE_UnitParts",
    "TABLE_Instances",
    "Type",
    "Types",
    "types",
    "Prop",
    "Props",
    "props",
    "Trait",
    "Traits",
    "traits",
    "TypeTrait",
    "TypeTraits",
    "type_traits",
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
