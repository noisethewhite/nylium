# ADR-0001: Passkey auth + deployment

Status: accepted (2026-09-02). Amended 2026-09-02: deploy target moved from
atos to personal_vps (217.160.4.50, Debian 13, root). Domain changed to
`nylium.noisethewhite.dev` — RP_ID/RP_ORIGIN follow the domain, so passkeys
registered under the old RP are invalid. Runtime is now a system unit
(`/etc/systemd/system/nylium.service`, `WorkingDirectory=/opt/nylium`,
`Restart=always`); Postgres runs natively on the VPS (Debian postgresql-17,
data in `/var/lib/postgresql`), no Docker. Caddy on the VPS terminates TLS.
GH secrets: `VPS_SSH_KEY`; vars: `VPS_HOST`, `VPS_USER`. The `systemd --user`
+ atos specifics below are superseded.
Date: 2026-09-02

## Context

nylium goes live at `https://nylium.grimaud.noisethewhite.dev`.

Recon facts:

- The domain already resolves to atos (49.12.33.15) — this machine.
- Caddy on atos terminates TLS and has a route
  `nylium.grimaud.noisethewhite.dev → 127.0.0.1:8474`, currently
  guarded by Caddy HTTP basic auth (user `max`). Nothing listens on
  8474 yet.
- `StaticSpa` already serves `web/dist` from the FastAPI process with
  SPA fallback: the deployable is one uvicorn process.
- Postgres runs on atos via `compose.yaml` (db only), healthy.
- The app has no auth at all; the requirement is passkey (WebAuthn)
  login, replacing the basic-auth layer — no passwords anywhere.

## Decisions

### Auth (WebAuthn / passkeys)

1. **Libraries**: `py_webauthn` (server ceremonies),
   `@simplewebauthn/browser` (client). No crypto by hand.
2. **RP config** via `Environment`: `rp_id`
   (`nylium.grimaud.noisethewhite.dev` in prod), `rp_origin`
   (`https://nylium.grimaud.noisethewhite.dev` in prod). Dev/tests set
   localhost values explicitly through `Environment`, same convention
   as `database_url`.
3. **Storage: system tables in `database/tables.py`, not nylium
   objects.** Auth is infrastructure, not domain data — and the nylium
   type system has no Blob scalar for public keys / credential IDs.
   Tables:
   - `auth_users(uuid pk, name unique, created_at)`
   - `auth_credentials(uuid pk, user_uuid fk → auth_users,
     credential_id bytea unique, public_key bytea, sign_count bigint,
     transports text, created_at, last_used_at null)`
   - `auth_challenges(challenge bytea pk, kind register|login,
     user_uuid fk null, expires_at)` — 5-minute TTL, consumed on use
   - `auth_sessions(token_hash text pk, user_uuid fk, expires_at)` —
     token is 32 random bytes in the cookie, sha256 hex stored
4. **Endpoints** (all under `/api/auth`, the only unauthenticated
   prefix besides static):
   - `POST /api/auth/login/start` → PublicKeyCredentialRequestOptions
   - `POST /api/auth/login/finish` → sets session cookie
   - `POST /api/auth/register/start|finish` → registration ceremony
   - `POST /api/auth/logout`, `GET /api/auth/me`
5. **Bootstrap policy**: registration is open only while
   `auth_credentials` is empty — the first passkey creates the owner
   account. After that, `register/*` requires a valid session (adding
   keys = being logged in). Single-owner in practice, multi-user
   schema from day one.
6. **Session cookie**: `nylium_session`, HttpOnly, Secure,
   SameSite=Lax, 30 days, sliding (expiry extended on use).
7. **Guard**: a FastAPI dependency on every `/api` route except
   `/api/auth/*`; static SPA stays public — it *is* the login screen.
8. **Frontend**: login view with a single "Sign in with passkey"
   button (and registration variant on a fresh install). Auth state
   from `GET /api/auth/me`; 401 → login view.
9. **Caddy**: once passkey login is verified live, drop the
   `http_basic` handler from the `nylium` route — both the live config
   (Admin API PATCH) and `caddy-routes.service`.

### Deployment

10. **Runtime**: `systemd --user` unit `nylium.service` on atos —
    uvicorn on `127.0.0.1:8474`, `DATABASE_URL` from the unit's
    EnvironmentFile, `Restart=on-failure`. Deploy dir
    `~/services/nylium` (separate from `~/projects/nylium` dev repo).
11. **CI workflow** (`.github/workflows/ci.yml`, on push/PR):
    postgres service container → `uv sync` → `pytest` →
    `basedpyright` → `npm ci` → `npm run check` → `npm run build`.
12. **Deploy workflow** (`.github/workflows/deploy.yml`, on push to
    main, gated by CI): build `web/dist` on the runner → rsync the
    tree to atos → `uv sync --frozen` on atos →
    `systemctl --user restart nylium` → healthcheck (`curl` expects
    401 from a guarded endpoint). Dedicated ed25519 deploy key in GH
    secrets (`DEPLOY_SSH_KEY`), authorized for user `atos`.
13. **No docker image / registry**: one host, one service; rsync is
    the smallest thing that works.

## Consequences

- No passwords anywhere: basic-auth popup disappears, login is a
  platform passkey (Touch ID on the Mac, etc.).
- Losing all passkeys on a non-empty install = DB-level recovery
  (delete rows in `auth_credentials` to reopen bootstrap). Accepted:
  single-owner system.
- Dev flow unchanged; a fresh dev DB shows the registration screen
  first.

## LOC estimate

Backend ~400 (tables, ceremonies, guard, endpoints), frontend ~200
(login view, simplewebauthn calls), workflows + unit ~150. Over the
250-LOC bar — implementation starts only after this ADR is approved.
