"""Row snapshots for the domain-object tables.

The value half of the domain-object split (ADR-0019): each mapped
``TABLE_<Name>`` in ``nylium.objects.tables`` has a Row subclass here
(``type.py``, ``prop.py``, …) carrying the column-backed attributes.
These are the in-memory facades over a single DB row.

Import deliberately minimal: rows re-export nothing at package level to
avoid import cycles (rows ↔ tables are mutually referential at the module
level). Import a specific Row from its submodule.
"""
