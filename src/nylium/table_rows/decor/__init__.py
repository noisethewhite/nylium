"""Decor tables — mapped Rows + their stores, one file per table (ADR-0033)."""
from nylium.table_rows.decor.trait_decor import TraitDecor, TraitDecors, trait_decor
from nylium.table_rows.decor.type_decor import TypeDecor, TypeDecors, type_decor

__all__ = [
    "TraitDecor",
    "TraitDecors",
    "TypeDecor",
    "TypeDecors",
    "trait_decor",
    "type_decor",
]
