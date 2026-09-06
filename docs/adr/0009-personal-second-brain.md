# ADR-0009: Personal second brain — tasks, events, notes, calendar, agent access

- Status: accepted (2026-09-06)
- Date: 2026-09-06

## Context

Two problems, one structure. Max (ADHD) loses track of what to do and what
was decided; Grimaud (the assistant) has a full, partly stale memory and can
invent facts on the fly. Both need a single external source of truth — not
another chat log, but a durable place where tasks, events, decisions and
people-facts live and are read back.

nylium is already a generic typed object store with the scalars this needs
out of the box (`String`, `Integer`, `Numeric`, `Boolean`, `Datetime`,
`Date`, `Time`, `Color`, `MonthDay`, `MonthDayTime`) plus Enum, Unit,
Function and Embedded kinds. Types are created with `WType.ensure` and
props with `WProp.ensure` — so "tasks / events / notes / people" are
**data**, not new engine code.

Hard constraints from Max:

- **Single-user** for now — no sharing, no multi-user, no invitations.
- **Private** — personal life must not be visible to anyone else, and
  nothing here is published or linked publicly.
- **A calendar** — events and deadlines need a date-grid view, not a table.
- **ADR first** — no code until this is accepted.

## Decision

### 1. Domain types are user data, not engine builtins

The second brain is a *use* of nylium, not a product feature. Its types are
ordinary user-defined types, seeded once into the prod database via the
existing `WType.ensure` + `WProp.ensure` path (a small idempotent seed
script), and are **not** added to `ensure_builtins`. Personal schema must
not leak into the engine's core types.

Seeded types:

| Type | Kind | Props |
|---|---|---|
| `TaskStatus` | Enum | `todo`, `doing`, `done` |
| `Priority` | Enum | `low`, `medium`, `high` |
| `Task` | Object | `title` String · `status` TaskStatus · `priority` Priority · `due` Date · `tags` Array\<String\> · `notes` String |
| `Event` | Object | `title` String · `start` Datetime · `end` Datetime · `location` String · `notes` String |
| `Note` | Object | `title` String · `body` String · `tags` Array\<String\> · `category` String |
| `Person` | Object | `name` String · `role` String · `contact` String · `notes` String |

Computed helpers (overdue, "next up by priority") are deferred to a second
iteration via the existing formula mechanism (ADR-0005); the MVP uses plain
stored props.

### 2. Calendar view — a generic date-grid feature

A new **Calendar** surface in the frontend renders objects on a month grid
(week/day views later). It is generic, not Task/Event-specific: an object is
shown on the calendar when it has a prop of type `Date`/`Datetime`. For the
MVP the mapping is by convention — `Event.start` (with `end` as the span)
and `Task.due` — but the underlying view reads any date-typed prop, so a
future "show my `Note.reminder_on` here too" is configuration, not a new
feature.

### 3. Agent access token — programmatic read/write for Grimaud

Auth today is passkey (WebAuthn) + a session cookie; there is no way for a
non-interactive client to reach the API. Add an **API token** layer:

- `api_tokens` table: `uuid`, `name`, `token_hash` (sha256), `scope`
  (read / read-write), `created_at`, `last_used_at`, `revoked_at`.
- `Authorization: Bearer <token>` accepted on `/api/*`, resolved by the
  existing guard; a token authenticates as its owning user.
- Scoped and revocable — the token is for Grimaud's automation only, and it
  never grants access beyond the single owner account.

This is a reusable auth primitive (any script/agent can hold one), not a
one-off back door — universality over a bespoke "grimaud can write" flag.

### 4. Reminders — a Hermes cron, not a nylium feature

Notifications are a transport concern and live outside nylium. A Hermes cron
job reads nylium through the agent token (Task `due`, Event `start`) and
sends reminders to Max's Telegram. nylium stays a passive store; nothing in
the engine sends messages.

### 5. Privacy boundary — explicit, non-negotiable

- Single-user: no multi-user, sharing, or invitation surface is added.
- Passkey auth remains the only human entry; the API token is scoped,
  revocable and audited (`last_used_at`).
- No public links, public export, or public read of any second-brain data.
- `nylium.noisethewhite.dev` remains a private single-owner install; the
  second-brain content is not published anywhere.

## Consequences

- Tasks/events/notes/people become queryable, dated, and reviewable in one
  place instead of decaying in chat history.
- Grimaud gains a canonical source to read before advising and write after
  learning a fact — the fix for both "forgets" and "invents".
- Two new engine features (calendar view, API token) land in the nylium
  codebase; the domain types do not (they are data).
- Prod `.env` gains nothing new for the seed path (types are data rows), but
  the API-token feature is a push-order gate: any new env var must land in
  `/opt/nylium/.env` before deploy.

## Rejected

- **Separate second-brain instance.** A second install doubles the ops
  surface and re-opens the "which one is current" problem. Dogfooding the
  existing single-user prod is simpler and keeps the product honest.
- **Obsidian / dedicated notes app.** Adds a second storage system instead
  of making nylium useful; the point is to give nylium (typed, dated,
  computed) a reason to exist for Max personally.
- **Direct DB access for Grimaud instead of an API token.** Bypasses the
  guard, couples the agent to the schema, and can't be scoped/revoked
  cleanly. An API token is the auditable seam.
- **Seed second-brain types as engine builtins.** Personal schema in the
  core `ensure_builtins` would make the engine carry one user's domain
  model; they belong in the prod database as data.

## LOC estimate

Calendar view (frontend) ~300–400; API-token layer (backend) ~100–150;
domain-type seed script ~50 (one-off, data). Over the 250-LOC bar —
implementation starts only after this ADR is accepted.
