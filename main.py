from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title='Task API', version='1.0')


class Task(BaseModel):
    id: int
    title: str
    done: bool


class CreateTaskRequest(BaseModel):
    title: str | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    done: bool | None = None


tasks: list[Task] = [
    Task(id=1, title='Read assignment', done=False),
    Task(id=2, title='Build API endpoints', done=False),
    Task(id=3, title='Test with Swagger UI', done=False),
]

seed_tasks: list[Task] = [task.model_copy(deep=True) for task in tasks]


def find_task(task_id: int) -> Task | None:
    for task in tasks:
        if task.id == task_id:
            return task
    return None


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


@app.get('/tasks', summary='List tasks', description='Returns all tasks from in-memory storage. Supports done and search filters.')
def list_tasks(done: bool | None = None, search: str | None = None) -> list[Task]:
    filtered = tasks

    if done is not None:
        filtered = [task for task in filtered if task.done == done]

    if search is not None:
        term = search.strip().lower()
        if term:
            filtered = [task for task in filtered if term in task.title.lower()]

    return filtered


@app.get('/tasks/{task_id}', summary='Get one task', description='Returns one task by id or a 404 JSON error if it does not exist.')
def get_task(task_id: int) -> Task:
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={'error': f'Task {task_id} not found'})
    return task


@app.post('/tasks', status_code=status.HTTP_201_CREATED, summary='Create task', description='Creates a task from title, sets done=false, and returns the created task.')
def create_task(payload: CreateTaskRequest) -> Task:
    title = clean_title(payload.title)
    if title is None:
        raise HTTPException(status_code=400, detail={'error': 'title is required and cannot be empty'})

    next_id = max([task.id for task in tasks], default=0) + 1
    new_task = Task(id=next_id, title=title, done=False)
    tasks.append(new_task)
    return new_task


@app.put('/tasks/{task_id}', summary='Update task', description='Updates title and/or done for an existing task.')
def update_task(task_id: int, payload: UpdateTaskRequest) -> Task:
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={'error': f'Task {task_id} not found'})

    has_title = payload.title is not None
    has_done = payload.done is not None
    if not has_title and not has_done:
        raise HTTPException(status_code=400, detail={'error': 'request body must include title and/or done'})

    if has_title:
        title = clean_title(payload.title)
        if title is None:
            raise HTTPException(status_code=400, detail={'error': 'title cannot be empty'})
        task.title = title

    if has_done:
        task.done = payload.done

    return task


@app.delete('/tasks/{task_id}', status_code=status.HTTP_204_NO_CONTENT, summary='Delete task', description='Deletes a task by id.')
def delete_task(task_id: int) -> Response:
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={'error': f'Task {task_id} not found'})

    tasks.remove(task)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get('/stats', summary='Task stats', description='Returns aggregate counts for all, completed, and open tasks.')
def task_stats() -> dict:
    done_count = sum(1 for task in tasks if task.done)
    total = len(tasks)
    return {'total': total, 'done': done_count, 'open': total - done_count}


@app.post('/reset', summary='Reset tasks', description='Restores the initial three example tasks in memory.')
def reset_tasks() -> list[Task]:
    tasks.clear()
    tasks.extend(task.model_copy(deep=True) for task in seed_tasks)
    return tasks


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    if isinstance(exc.detail, dict) and 'error' in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={'error': 'request failed'})
