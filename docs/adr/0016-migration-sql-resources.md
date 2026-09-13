# ADR-0016: Migration SQL as packaged resources

## Status

Accepted (2026-09-13)

## Context

`server/app.py` built its idempotent boot migrations as Python string
literals — concatenated `+`-joined SQL, including f-string interpolation
of an `IN (...)` tuple in `_migrate_files_to_first_class`. That violates
the foreign-languages principle (SQL is string soup when embedded in
host-language files) and had already cost readability: the file-kind
tuple was a Python variable interpolated into four different statements.

## Decision

Migration SQL lives in `src/nylium/server/migrations/` as `.sql`
resource files — one statement per file, grouped in subdirectories
(`schema/`, `decor/`, `files_first_class/`, `type_colors/`,
`file_kinds.sql`). Statement order inside a group is filename order
(numeric prefixes); the filesystem is the single source of truth for
order — no manifest duplicated in Python.

The `migrations` namespace class loads them via `importlib.resources`:

- `migrations.group("schema")` → `list[str]`, filename-sorted;
- `migrations.statement("file_kinds.sql")` → single file contents.

`server/app.py` wraps the loaded strings in `sqlalchemy.text()` — the
sanctioned loader pattern. Parameterized statements (the type-color
palette rewrite) keep `:name`-style bind params in the `.sql` file and
receive values at the call site.

Non-DDL single-shot queries in business code use the SQLAlchemy
expression API instead of resource files (e.g. the
`pg_database_size(current_database())` probe in `api/files.py` became
`sqla.select(sqla.func.pg_database_size(...))`).

## Consequences

- All migration SQL is syntax-highlightable, grep-able, and reviewable
  as SQL.
- No string interpolation into SQL remains anywhere in the codebase.
- Migrations stay immutable once shipped: new schema changes append new
  numbered files, never edit existing ones.
