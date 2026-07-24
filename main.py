from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title='Task API', version='1.0')


class Task(BaseModel):
    id: int
    title: str
    done: bool


tasks: list[Task] = [
    Task(id=1, title='Read assignment', done=False),
    Task(id=2, title='Build API endpoints', done=False),
    Task(id=3, title='Test with Swagger UI', done=False),
]


def find_task(task_id: int) -> Task | None:
    for task in tasks:
        if task.id == task_id:
            return task
    return None


@app.get('/')
def root() -> dict:
    return {'name': 'Task API', 'version': '1.0', 'endpoints': ['/tasks']}


@app.get('/health')
def health() -> dict:
    return {'status': 'ok'}


@app.get('/tasks')
def list_tasks() -> list[Task]:
    return tasks


@app.get('/tasks/{task_id}')
def get_task(task_id: int) -> Task:
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={'error': f'Task {task_id} not found'})
    return task


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    if isinstance(exc.detail, dict) and 'error' in exc.detail:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={'error': 'request failed'})
