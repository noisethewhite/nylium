"""Mapped domain-object tables, their Table stores, and Row snapshots.

The domain-object persistence layer: the type registry, instances and
their props, plus the parameter tables for enum and unit types
(ADR-0011). Raw SQLAlchemy ``TABLE_*`` classes (``table_<name>.py``),
the Table mapping + singleton stores (``<name>s.py``), and the Row
snapshots they map onto (``<name>.py``) all live together in this flat
package again (ADR-0030 reverses the ADR-0019 domain/object split).

Import order below is load-bearing: each module is imported only after
its dependencies (types last, after enum_options/unit_parts it renders).
"""
from nylium.tables.objects.table_types import TABLE_Types
from nylium.tables.objects.props import TABLE_Props, Prop, Props, props
from nylium.tables.objects.traits import (
    TABLE_Traits,
    TABLE_TypeTraits,
    Trait,
    Traits,
    TypeTrait,
    TypeTraits,
    traits,
    type_traits,
)
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
]
