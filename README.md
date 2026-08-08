# Task API (FastAPI + Postgres, containerized)

CRUD task API running against a real PostgreSQL database in Docker. This is the third
storage swap in the lane: memory (A1) -> SQLite (A2) -> containerized Postgres (this one,
A3). The API is unchanged across all three - only the storage engine underneath moved.

## Run everything with one command

```bash
cp .env.example .env
docker compose up
```

That builds the `api` image, starts Postgres (`db`) with a named volume, waits for Postgres
to report healthy, then starts the API on **http://localhost:8000**. The `tasks` table and
its three seed rows are created automatically on first boot - nothing to set up by hand.

Stop everything with `docker compose down` (add `-v` only if you *want* to wipe the volume
and lose your data).

## Environment variables

Copy `.env.example` to `.env` and adjust if needed:

| Variable | Purpose | Example |
|---|---|---|
| `DATABASE_URL` | Postgres connection string | `postgres://postgres:dev@localhost:5432/tasks` |

`.env` is git-ignored - it never leaves your machine. Under `docker compose`, the `api`
service gets `DATABASE_URL` from `compose.yaml` instead (pointed at the `db` service name,
not `localhost`), so `.env` only matters when running the app outside of Compose.

## Run without Compose (for local development)

```bash
# 1. Start Postgres by itself
docker run --name taskdb -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks \
  -p 5432:5432 -v taskdata:/var/lib/postgresql/data -d postgres

# 2. Install deps and run the app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

## Why Postgres, why Docker

Assignment A1 stored tasks in memory (gone on restart); A2 moved them into a SQLite file
(persisted, but still a single-process, single-file engine). This assignment swaps in
PostgreSQL - a real database server, the same kind that runs a large share of production
backends - so the project behaves like a real deployed service: a separate database process
your API connects to over the network, capable of handling multiple concurrent clients
safely. Docker means nobody has to install or configure Postgres by hand: the official
`postgres` image is a ready-made, disposable box that behaves identically on every machine
and kills "works on my machine" for good. Combined with `docker compose up`, a stranger gets
a working stack - app and database both - in one command.

## Endpoints

| Method | Path | Purpose | Success | Error cases |
|---|---|---|---|---|
| GET | / | API metadata | 200 | - |
| GET | /health | Pings Postgres (`SELECT 1`) and reports db status | 200 (or 503 if db unreachable) | - |
| GET | /tasks | List all tasks | 200 | - |
| GET | /tasks?done=true | Filter tasks by completion | 200 | - |
| GET | /tasks?search=milk | Search tasks by title substring | 200 | - |
| GET | /tasks/{id} | Get one task | 200 | 404 if id not found |
| POST | /tasks | Create task | 201 | 400 for missing/empty title |
| PUT | /tasks/{id} | Update title and/or done | 200 | 400 for invalid body, 404 if id not found |
| DELETE | /tasks/{id} | Delete task | 204 | 404 if id not found |
| GET | /stats | Task counts (total, done, open) | 200 | - |
| POST | /reset | Reset to the 3 seed tasks | 200 | - |

Swagger UI: http://localhost:8000/docs

## Example curl -i output

```bash
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Buy milk"}'
```

Expected response:

```http
HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

## Persistence, proven two ways

1. **Via the API**: create a task, `docker compose down`, `docker compose up` again, then
   `GET /tasks` - the task is still there because `taskdata` is a named volume, not
   container-local storage.
2. **Via the database directly**: `docker exec -it <db container> psql -U postgres -d tasks -c "SELECT * FROM tasks;"`
   shows the exact same rows the API just returned - proof there's one source of truth, not
   a cache that happens to agree with it.

## Why volumes matter

Run Postgres *without* a volume, create a task, `docker rm` the container, and start a fresh
one: the task is gone. A container's writable layer dies with the container: a volume is
storage that lives outside the container's lifecycle, so the database process can be
destroyed and recreated (for an upgrade, a crash, a redeploy) without losing a single row.

## Database screenshot

_Add a screenshot here (`docs/db-screenshot.png`) showing `\dt` and a `SELECT * FROM tasks;`
from `psql`, or from a GUI like DBeaver / pgAdmin / TablePlus, once you've run
`docker compose up` locally._

```markdown
![Postgres data](docs/db-screenshot.png)
```

## Tests

Unit tests cover every endpoint, status code (200/201/204/400/404), and validation rule.
They're the same tests written for the A1/A2 in-memory/SQLite versions, run unchanged
against Postgres - identical tests passing across three different storage engines is the
proof that storage really is just an implementation detail behind a stable API contract
(see A15 - Layered architecture, for where this separation gets formalized into its own
layer).

Postgres must be running first (`docker compose up -d db`, or the standalone `docker run`
above):

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Prove the swap

Across A1 (memory), A2 (SQLite), and A3 (Postgres), the exact same request to
`POST /tasks` returns the exact same shaped response, and the exact same test suite passes
against all three. That's only possible because every database line lives in one module,
`repository.py` - the routes in `main.py` never changed, only what's behind them did.

## Notes

- The database is created automatically - `CREATE TABLE IF NOT EXISTS`, then three seed
  tasks only if the table is empty, so restarting (or `docker compose down && up`) never
  duplicates them.
- All queries use `%s` parameterized placeholders (psycopg) - no request value is ever glued
  into a SQL string.
- `.env` is git-ignored; `.env.example` is committed with the same keys and placeholder
  values so a stranger knows exactly what to set.

## Optional extras implemented

- Query filtering with `done` (true/false)
- Query search with `search` text
- Stats endpoint at `/stats`
- Reset endpoint at `/reset`
- Real health check: `/health` runs `SELECT 1` against Postgres and reports `db: "ok"` (or
  `503` with `db: "unreachable"`) instead of a static OK - the kind of check a load balancer
  gates deploys and routing decisions on.
