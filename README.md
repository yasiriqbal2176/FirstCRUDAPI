# Task API (FastAPI)

Small CRUD API for a to-do list using SQLite persistence instead of in-memory storage.

## Why SQLite

SQLite was chosen over a client/server database because it needs no separate install or
process — the entire database is one file (`tasks.db`) that Python's built-in `sqlite3`
module opens directly. For a small single-process API like this one, that means zero setup
for anyone who clones the repo, and — unlike the in-memory list from Assignment 1 — the data
now survives a server restart because it lives on disk instead of in a variable that gets
wiped when the process exits.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open:
- API root: http://localhost:8000/
- Health: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs

## Endpoints

| Method | Path | Purpose | Success | Error cases |
|---|---|---|---|---|
| GET | / | API metadata | 200 | - |
| GET | /health | Health check | 200 | - |
| GET | /tasks | List all tasks | 200 | - |
| GET | /tasks/{id} | Get one task | 200 | 404 if id not found |
| POST | /tasks | Create task | 201 | 400 for missing/empty title |
| PUT | /tasks/{id} | Update title and/or done | 200 | 400 for invalid body, 404 if id not found |
| DELETE | /tasks/{id} | Delete task | 204 | 404 if id not found |
| GET | /tasks?done=true | Filter tasks by completion | 200 | - |
| GET | /tasks?search=milk | Search tasks by title substring | 200 | - |
| GET | /stats | Task counts (total, done, open) | 200 | - |
| POST | /reset | Reset to the 3 seed tasks | 200 | - |

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

## Tests

Unit tests cover every endpoint, status code (200/201/204/400/404), and validation rule. These
are the same tests written for the in-memory Assignment 1 API, run unchanged against this
SQLite-backed version.

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

All 40 tests pass without any modification to the test file itself. That's the proof that the
storage swap worked: the tests only talk to the API (the promise), never to `tasks.db` (where
the promise is kept), so identical tests passing before and after means the database is truly
just an implementation detail behind an unchanged API.

## Notes

- Data now lives in `tasks.db`, which is created automatically (SQLite creates the file the
  first time the app opens it) and survives restarts — the `tasks` table is created with
  `CREATE TABLE IF NOT EXISTS` and seeded with 3 example tasks only when the table is empty,
  so restarting never duplicates them.
- The database file is ignored by Git (see `.gitignore`) so each fresh clone starts clean and
  regenerates its own `tasks.db` on first run.
- Example SQL from the database stage, run by hand in DB Browser for SQLite:

```sql
SELECT * FROM tasks;
```

This returned the 3 seeded rows (`Read assignment`, `Build API endpoints`,
`Test with Swagger UI`, each with `done = 0`) — the exact same rows `GET /tasks` returns,
confirming the API and DB Browser are reading the same file with no syncing involved.

## Database Screenshot

DB Browser for SQLite view of the seeded database:

![DB Browser screenshot](docs/db-browser-screenshot.png)

## Swagger Screenshot

![Swagger UI](docs/swagger-ui.png)

## Optional extras implemented

- Query filtering with `done` (true/false)
- Query search with `search` text
- Stats endpoint at `/stats`
- Reset endpoint at `/reset`
