# ADR-0006: File types and blob storage

- Status: accepted
- Date: 2026-09-04

## Context

Objects currently carry only inline values (scalars, refs, arrays, embedded
children). Real workspaces need attachments: PDFs, photos, scans. Three
builtin types cover it: **File** (any blob), **Document** (semantic bucket
for texts/PDFs), **Image** (raster/vector images, also usable as type
icons).

Hard requirements from the product side:

1. An instance of File/Document/Image is a **pointer** to a stored blob.
2. Renaming the *original* file on the client machine changes nothing —
   links from other objects survive. (Trivially true once blobs are keyed
   by instance uuid, but stated because it rules out filename-keyed
   storage.)
3. An Image instance can serve as a type's icon instead of a Material
   Symbols glyph.

## Decision

### Types

Three builtin object-kind types, seeded like the other builtins
(`ensure_builtins`): `File`, `Document`, `Image`. Each has the pinned
`name` prop (defaults to the uploaded file's original name, freely
editable — this is the display name, never the storage key). No other
props; users cannot add props to file types (same restriction as
builtins elsewhere).

MIME policy (confirmed with Max, 2026-09-04):

- `Image` — server rejects non-`image/*` uploads (422).
- `Document` — strict allow-list (422 otherwise): `application/pdf`,
  `application/msword`, `application/vnd.openxmlformats-officedocument.*`,
  `application/vnd.oasis.opendocument.*`, `text/plain`, `text/markdown`,
  `text/csv`, `application/rtf`, `application/epub+zip`. One frozen set
  in code (`DOCUMENT_MIMES`), not per-instance config.
- `File` — any MIME accepted.

File types are not embedded, not enum/unit. `Array<Image>` etc. work
through the existing array machinery with no special casing.

### Storage

Blobs live in a dedicated directory, env `FILES_DIR` (new `Environment`
member, **required** — `EnvEnum` rejects empty vars, so dev sets
`./files`, prod `/opt/nylium/files`). **Blob filename = instance uuid**,
no extension. Original filename and MIME are metadata, not storage
keys — requirement 2 holds by construction.

Metadata table `files`: `uuid PK → objects.uuid` (the instance),
`mime TEXT`, `size_bytes BIGINT`. The blob lives only on disk; the row
exists only while the instance exists.

### API

- `POST /api/files` — multipart (`file`, `type_name` ∈ {File, Document,
  Image}). Atomically: validate MIME → create instance (name = original
  filename) → write blob to `FILES_DIR/<uuid>` → insert `files` row.
  Any failure rolls back both the DB and the partial blob.
- `GET /api/files/{uuid}` — streams the blob with stored MIME
  (`FileResponse`), `Content-Disposition: inline; filename*=UTF-8''<name>`
  so browsers render images and offer the original name on download.
- Upload cap: 25 MiB (`MAX_UPLOAD_BYTES` constant, 413 over it).
- Deleting the instance deletes blob + row (cascade in the existing
  delete path). Deleting via `DELETE /api/objects/{uuid}` only — no
  separate file endpoint.
- Orphan sweep on startup: blobs on disk with no `files` row are
  deleted (crash-window cleanup, logged).

`ObjectView` for file-type instances gains nothing — `mime`/`size` come
from `GET /api/files/{uuid}` headers. The frontend knows the uuid from
the object itself.

### Type icons

`types.icon` stays one TEXT column. Two value shapes:

- glyph name (today), or
- `img:<uuid>` — uuid of an existing `Image` instance.

Validation in `_check_icon`: `img:` values must parse as a uuid of a
live Image instance (422 otherwise). Deleting an Image that is used as
an icon is **allowed** (confirmed with Max, 2026-09-04): the type's
`types.icon` is reset to the default glyph in the same transaction, so
no dangling `img:` value ever exists. Frontend `TypeIcon` renders
`<img src="/api/files/<uuid>">` for `img:` values, glyph otherwise;
icon picker gains an "upload image" affordance next to the swatch row.

## Consequences

- New `Environment.files_dir` — prod systemd unit + CI deploy env need
  it; documented in the deploy runbook.
- Backup story: `pg_dump` no longer suffices alone; `FILES_DIR` tarred
  alongside.
- 25 MiB cap is a floor decision — bumping it is a constant change, no
  schema impact.
- No dedup/content hashing: two uploads of the same bytes are two
  instances. Simplicity beats storage golf at this scale.

## Rejected

- **Filename-keyed blobs** — violates requirement 2 on every rename of
  the display name.
- **A fourth kind `file` mirroring enum/unit** — files are object-kind
  with a fixed shape; a whole kind buys nothing and drags the full
  ladder.
- **Separate `icon_image_uuid` column on types** — one column, two
  shapes keeps the icon contract single-sourced; the `img:` prefix is
  unambiguous (glyph names are `[a-z_]+`).
- **MIME allow-list for File** — File is the "whatever else" bucket;
  restricting it defeats its purpose.
