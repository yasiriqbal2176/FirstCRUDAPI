# Task API (FastAPI)

Small CRUD API for a to-do list using in-memory storage (no database).

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

## Notes

- Data is in-memory and resets on server restart.
- Add your Swagger UI screenshot here for Stage 5 submission.

## Optional extras implemented

- Query filtering with `done` (true/false)
- Query search with `search` text
- Stats endpoint at `/stats`
- Reset endpoint at `/reset`
