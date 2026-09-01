# nylium

## Dev setup

Database (the only service that runs in Docker):

```
docker compose up -d db   # start Postgres
docker compose stop db    # stop (data persists in the db-data volume)
docker compose down -v    # stop AND wipe the database entirely
```

Copy `.env.example` to `.env` (tests and the server read `DATABASE_URL` from it):

```
cp .env.example .env
```

Backend + tests (native, via uv):

```
uv sync
uv run pytest
```

Frontend (native, via npm):

```
npm install
npm run dev      # vite dev server
npm run build    # production build into web/dist
```

If `docker compose up -d db` fails with "port 5432 is already allocated" — a leftover
local Postgres is still running (`pg_ctl -D .pgdata stop` / `brew services stop postgresql`).
