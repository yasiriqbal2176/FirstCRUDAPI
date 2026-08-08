from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import repository

load_dotenv()

app = FastAPI(title='Task API', version='1.0')

repository.init_db()


class Task(BaseModel):
    id: int
    title: str
    done: bool


class CreateTaskRequest(BaseModel):
    title: str | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    done: bool | None = None


def clean_title(raw_title: str | None) -> str | None:
    if raw_title is None:
        return None
    title = raw_title.strip()
    if not title:
        return None
    return title


@app.get('/', summary='API metadata', description='Returns the API name, version, and top-level endpoints.')
def root() -> dict:
    return {'name': 'Task API', 'version': '1.0', 'endpoints': ['/tasks']}


@app.get('/health', summary='Health check', description='Returns an OK status so monitors can verify the server is running.')
def health() -> dict:
    return {'status': 'ok'}


@app.get('/tasks', summary='List tasks', description='Returns all tasks from Postgres.')
def list_tasks() -> list[Task]:
    return [Task(**row) for row in repository.list_tasks()]


@app.get('/tasks/{task_id}', summary='Get one task', description='Returns one task by id or a 404 JSON error if it does not exist.')
def get_task(task_id: int) -> Task:
    row = repository.get_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail={'error': 'Task not found'})
    return Task(**row)


@app.post('/tasks', status_code=status.HTTP_201_CREATED, summary='Create task', description='Creates a task in Postgres from title, sets done=false, and returns the created task.')
def create_task(payload: CreateTaskRequest) -> Task:
    title = clean_title(payload.title)
    if title is None:
        raise HTTPException(status_code=400, detail={'error': 'title is required and cannot be empty'})
    row = repository.create_task(title)
    return Task(**row)


@app.put('/tasks/{task_id}', summary='Update task', description='Updates title and/or done for an existing task in Postgres.')
def update_task(task_id: int, payload: UpdateTaskRequest) -> Task:
    existing = repository.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail={'error': 'Task not found'})

    has_title = payload.title is not None
    has_done = payload.done is not None
    if not has_title and not has_done:
        raise HTTPException(status_code=400, detail={'error': 'request body must include title and/or done'})

    next_title = existing['title']
    next_done = existing['done']

    if has_title:
        title = clean_title(payload.title)
        if title is None:
            raise HTTPException(status_code=400, detail={'error': 'title cannot be empty'})
        next_title = title

    if has_done:
        next_done = payload.done

    row = repository.update_task(task_id, next_title, next_done)
    if row is None:
        raise HTTPException(status_code=404, detail={'error': 'Task not found'})
    return Task(**row)


@app.delete('/tasks/{task_id}', status_code=status.HTTP_204_NO_CONTENT, summary='Delete task', description='Deletes a task by id from Postgres.')
def delete_task(task_id: int) -> Response:
    deleted = repository.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={'error': 'Task not found'})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    if isinstance(exc.detail, dict) and 'error' in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={'error': 'request failed'})
