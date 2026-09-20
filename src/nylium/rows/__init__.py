"""Row snapshots (ADR-0031).

Each Row is a typed, writable snapshot of one ``TABLE_*`` row. The Row
classes live here, mirroring the ``tables`` package layout; the mapped
``TABLE_*`` classes and their ``Table`` stores stay in ``nylium.tables``.
Import a Row by its module (``nylium.rows.objects.type.Type``) or from the
matching store module, which re-exports it (``nylium.tables.objects.types.Type``).
"""
