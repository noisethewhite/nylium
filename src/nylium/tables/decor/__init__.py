"""ADR-0014: decorative attributes (plural form, icon, color) live apart
from the entity tables, one decor row per entity row, 1:1 mandatory.

``type_decor`` decorates ``types`` (plural_name/icon/color);
``trait_decor`` decorates ``traits`` (color). The entity's ``create``
writes both rows in one commit; deletes cascade through the FK.
"""
from __future__ import annotations

from nylium.tables.decor.table_type_decor import TABLE_TypeDecor
from nylium.rows.decor.type_decor import TypeDecor
from nylium.tables.decor.type_decors import TypeDecors, type_decor
from nylium.tables.decor.table_trait_decor import TABLE_TraitDecor
from nylium.rows.decor.trait_decor import TraitDecor
from nylium.tables.decor.trait_decors import TraitDecors, trait_decor

__all__ = [
    "TABLE_TraitDecor",
    "TABLE_TypeDecor",
    "TraitDecor",
    "TraitDecors",
    "TypeDecor",
    "TypeDecors",
    "trait_decor",
    "type_decor",
]
