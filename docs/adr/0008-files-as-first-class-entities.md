# ADR-0008: Files as first-class entities (out of the object model)

- Status: proposed
- Date: 2026-09-05

## Context

ADR-0006 shipped File/Document/Image as ordinary **object-kind Instances**:
the instance carries a pinned `name` prop (display name), a `files` row holds
mime/size, and the blob lives at `FILES_DIR/<instance uuid>`. Renaming never
touches the storage key because the key is the uuid, not the filename.

Two follow-ups now force a rethink:

1. **Files are not objects.** File/Document/Image must be their own rows in
   the Type Picker with behaviour distinct from Object (upload → blob, not
   edit-a-row). ADR-0006 explicitly rejected a fourth kind `file` and pinned
   files to object-kind; that decision no longer matches the product.
2. **The pointer must be stable by construction, not by convention.** Keeping
   the file as an Instance means its identity, display name and metadata are
   spread across three places (`instances`, a scalar value, `files`), and it
   is reachable by every generic object mutation (rename, delete, prop
   sync). Max wants file pointers in their own table so a rename is an
   `UPDATE files.name` and the reference (`files.uuid`) is untouched at the
   schema level.

## Decision

### Storage — one self-contained table

`files` becomes the single source of truth for a file entity, no longer a
metadata shard attached to an Instance:

- `uuid` — PK, **the pointer**; stable for the life of the file. Blob path
  stays `FILES_DIR/<uuid>`.
- `type_name` — one of `File` / `Document` / `Image`.
- `name` — display name (defaults to the original filename on upload, freely
  renameable).
- `mime` — TEXT.
- `size_bytes` — BIGINT.

The FK `files.uuid → instances.uuid` is dropped. File/Document/Image rows no
longer exist in `instances` at all, and their pinned `name` prop is gone —
`name` is a column here, not a scalar value.

### Types — a real `kind="file"`

File/Document/Image are seeded with `kind="file"` (a new `WType.KIND_FILE`),
reversing ADR-0006's "no fourth kind". They are **immutable** system types:
`rename_type`, `delete_type`, prop add/remove/sync and function-bind all
refuse them (`ValidationError` → 422), the same guard as scalars and
parameterized kinds. They remain separate rows in the Type Picker, never
grouped with Object.

### API — dedicated file endpoints

- `POST /api/files` — multipart upload (`file`, `type_name`). Atomically:
  validate MIME → insert `files` row → write blob to `FILES_DIR/<uuid>`.
  Rollback on failure, no partial blob.
- `GET /api/files/{uuid}` — stream blob (unchanged from ADR-0006).
- `GET /api/files` — list file entities (new).
- `PATCH /api/files/{uuid}` — rename `name` (new). The uuid/blob/references
  are untouched by definition.
- `DELETE /api/files/{uuid}` — delete row + blob (new; replaces
  `DELETE /api/objects/{uuid}` for files).

The file special-casing is removed from `delete_object` / object update: files
are no longer objects, so those paths never see them.

### References — uuid semantics preserved

A prop of type File/Document/Image stores a `files.uuid`. Migration keeps the
same uuid, so existing references survive untouched — only the resolver
changes: for file-typed props it reads `files` (name/mime) instead of
`instances`. `Array<Image>` and icon `img:<uuid>` go through the same
resolver.

### Migration

Idempotent, run in `_migrate_schema` on boot (and once in prod):

1. Add `type_name` and `name` columns to `files` (nullable → backfill →
   `NOT NULL`).
2. For every `instances` row whose type is File/Document/Image: read its
   `name` scalar and existing `files` mime/size, write `type_name` + `name`
   into the `files` row (same uuid), then delete the instance, its props and
   its scalar values.
3. Blobs are untouched (same uuid path).

### Frontend

- File entities leave the object list / sidebar Objects; a dedicated **Files**
  section lists them.
- File/Document/Image props render against `GET /api/files` (upload, rename,
  delete), not the object editor.
- Type Picker shows File/Document/Image as their own rows.

## Consequences

- Object model is simpler: files are not reachable through generic object
  mutation, so rename/delete of a file can never corrupt a pointer.
- Prod data migration is required before/at deploy (scripted, idempotent).
- New file list/rename/delete endpoints; the frontend file prop surface moves
  off the object editor.
- Backup story unchanged from ADR-0006: `pg_dump` + `FILES_DIR` tar.

## Rejected

- **Keep files as Instances, add `name` to `files` (hybrid).** Still leaves
  the file identity split across `instances` + a scalar + `files`, and still
  exposes files to generic object mutations — the pointer stability stays a
  convention, not a guarantee.
- **Filename-keyed blobs.** Already rejected in ADR-0006; re-affirmed.
