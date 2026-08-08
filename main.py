from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
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


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    if isinstance(exc.detail, dict) and 'error' in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={'error': 'request failed'})
