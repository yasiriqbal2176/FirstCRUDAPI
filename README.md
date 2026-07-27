# Task API (FastAPI)

Small CRUD API for a to-do list using SQLite persistence instead of in-memory storage.

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

Unit tests cover every endpoint, status code (200/201/204/400/404), and validation rule.

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Notes

- Data now lives in `tasks.db`, which is created automatically and survives restarts.
- The database file is ignored by Git so each fresh clone starts clean.
- Example SQL from the database stage:

```sql
SELECT * FROM tasks;
```

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
