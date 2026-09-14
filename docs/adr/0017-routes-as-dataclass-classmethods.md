# ADR-0017: Routes as classmethods of request dataclasses

## Status

Accepted (2026-09-14)

## Context

`server/routes.py` grew into a 30-handler namespace class whose only job
was adapting FastAPI plumbing to `Api` calls: handlers took loose path
scalars plus body DTOs from `server/bodies.py`, and responses were built
by calling `.wire()` on table objects, which returned untyped
`dict[str, object]`. Three problems followed:

1. The request shape was split between the signature (path params) and
   the DTO (body), so no single type described what a route accepts.
2. Responses crossing the HTTP boundary were untyped dicts — the wire
   contract lived only in `web/src/contracts.ts` and in tests, not in
   any checkable server-side type.
3. Serialization logic sat on table-domain objects (`.wire()`), pulling
   HTTP concerns into the storage layer — the exact inversion ADR-0011
   warned about for views.

## Decision

Every route is a `@classmethod route(...)` of its **request dataclass**:

- Body DTOs (`CreateTypeBody`, `SyncPropsBody`, …) stay in
  `server/bodies.py` and gain the classmethod. FastAPI binds path
  scalars from the URL and the dataclass itself from the JSON body in
  the same signature.
- GET/DELETE routes without a body get a small path-param request
  dataclass (`TypeNameRequest`, `ObjectUuidRequest`, …), bound via
  `Annotated[Self, Depends()]` so FastAPI reads the path parameters
  through the class signature. The file-level one-class-per-file
  exception in `bodies.py` is extended: these are peer request types of
  the same HTTP boundary.

Responses are typed view dataclasses in `server/views.py`: `TypeView`,
`TraitView`, `EnumOptionView`, `UnitPartView`, `PropView`, `FileView`,
`StorageStats` — pydantic dataclasses with `from_row` classmethod
constructors. They live in the server layer (unlike
`ObjectView`/`FunctionView` in `api/views.py`, which the `Api` facade
itself returns): the `Api` facade hands rows to the boundary and never
sees HTTP shapes. Serialization leaves the table layer: `.wire()` is
deleted from `Type`, `Trait`, `Prop`, `EnumOption`, `UnitPart`, and
`File` rows.

`server/routes.py` is deleted; `server/app.py` mounts the dataclass
classmethods directly (`CreateTypeBody.route`, …).

### Transport exceptions (explicit, not loopholes)

- `export_objects` returns `FileResponse` and `download_file` returns
  `Response` — binary payloads have no JSON dataclass form.
- `upload_file` takes `UploadFile` — multipart is FastAPI transport,
  not a JSON body.
- DELETE/`list_functions_of` still answer 204 with an empty body.
- `nylium/auth` routes (passkey ceremonies, token admin) are a separate
  subsystem with their own transport concerns and are out of scope here.

## Consequences

- Request and response shapes of every route are single named types;
  basedpyright checks the whole boundary, and the wire contract is
  discoverable without reading `contracts.ts`.
- Table objects no longer know JSON exists. Any change to a wire field
  is a change to a `views.py` dataclass, caught by type checking and by
  `tests/test_http.py` (36 wire-contract tests).
- The wire format itself is unchanged: pydantic serializes `UUID` and
  `Decimal` to strings in JSON mode exactly as `.wire()` did.
