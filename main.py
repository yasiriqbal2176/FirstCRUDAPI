import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title='Task API', version='1.0')
DB_PATH = Path(__file__).with_name('tasks.db')


class Task(BaseModel):
    id: int
    title: str
    done: bool


class CreateTaskRequest(BaseModel):
    title: str | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    done: bool | None = None


SEED_TASKS = [
    {'id': 1, 'title': 'Read assignment', 'done': 0},
    {'id': 2, 'title': 'Build API endpoints', 'done': 0},
    {'id': 3, 'title': 'Test with Swagger UI', 'done': 0},
]


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def row_to_task(row: sqlite3.Row) -> Task:
    return Task(id=row['id'], title=row['title'], done=bool(row['done']))


def fetch_task(task_id: int) -> Task | None:
    with get_db_connection() as connection:
        row = connection.execute(
            'SELECT id, title, done FROM tasks WHERE id = ?',
            (task_id,),
        ).fetchone()
    if row is None:
        return None
    return row_to_task(row)


def init_db() -> None:
    with get_db_connection() as connection:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            )
            '''
        )
        row = connection.execute('SELECT COUNT(*) AS count FROM tasks').fetchone()
        if row['count'] == 0:
            connection.executemany(
                'INSERT INTO tasks (id, title, done) VALUES (?, ?, ?)',
                [(task['id'], task['title'], task['done']) for task in SEED_TASKS],
            )


def reset_database() -> list[Task]:
    init_db()
    with get_db_connection() as connection:
        connection.execute('DELETE FROM tasks')
        connection.executemany(
            'INSERT INTO tasks (id, title, done) VALUES (?, ?, ?)',
            [(task['id'], task['title'], task['done']) for task in SEED_TASKS],
        )
        rows = connection.execute('SELECT id, title, done FROM tasks ORDER BY id').fetchall()
    return [row_to_task(row) for row in rows]


def clean_title(raw_title: str | None) -> str | None:
    if raw_title is None:
        return None
    title = raw_title.strip()
    if not title:
        return None
    return title


init_db()


@app.get('/', summary='API metadata', description='Returns the API name, version, and top-level endpoints.')
def root() -> dict:
    return {'name': 'Task API', 'version': '1.0', 'endpoints': ['/tasks']}


@app.get('/health', summary='Health check', description='Returns an OK status so monitors can verify the server is running.')
def health() -> dict:
    return {'status': 'ok'}


@app.get('/tasks', summary='List tasks', description='Returns all tasks from SQLite. Supports done and search filters.')
def list_tasks(done: bool | None = None, search: str | None = None) -> list[Task]:
    query = 'SELECT id, title, done FROM tasks'
    conditions: list[str] = []
    parameters: list[object] = []

    if done is not None:
        conditions.append('done = ?')
        parameters.append(int(done))

    if search is not None:
        term = search.strip()
        if term:
            conditions.append('LOWER(title) LIKE ?')
            parameters.append(f'%{term.lower()}%')

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY id'

    with get_db_connection() as connection:
        rows = connection.execute(query, parameters).fetchall()

    return [row_to_task(row) for row in rows]


@app.get('/tasks/{task_id}', summary='Get one task', description='Returns one task by id or a 404 JSON error if it does not exist.')
def get_task(task_id: int) -> Task:
    task = fetch_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={'error': 'Task not found'})
    return task


@app.post('/tasks', status_code=status.HTTP_201_CREATED, summary='Create task', description='Creates a task in SQLite from title, sets done=false, and returns the created task.')
def create_task(payload: CreateTaskRequest) -> Task:
    title = clean_title(payload.title)
    if title is None:
        raise HTTPException(status_code=400, detail={'error': 'title is required and cannot be empty'})

    with get_db_connection() as connection:
        cursor = connection.execute(
            'INSERT INTO tasks (title, done) VALUES (?, ?)',
            (title, 0),
        )
        task_id = cursor.lastrowid
        row = connection.execute(
            'SELECT id, title, done FROM tasks WHERE id = ?',
            (task_id,),
        ).fetchone()

    return row_to_task(row)


@app.put('/tasks/{task_id}', summary='Update task', description='Updates title and/or done for an existing task in SQLite.')
def update_task(task_id: int, payload: UpdateTaskRequest) -> Task:
    task = fetch_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={'error': 'Task not found'})

    has_title = payload.title is not None
    has_done = payload.done is not None
    if not has_title and not has_done:
        raise HTTPException(status_code=400, detail={'error': 'request body must include title and/or done'})

    next_title = task.title
    next_done = task.done

    if has_title:
        title = clean_title(payload.title)
        if title is None:
            raise HTTPException(status_code=400, detail={'error': 'title cannot be empty'})
        next_title = title

    if has_done:
        next_done = payload.done

    with get_db_connection() as connection:
        result = connection.execute(
            'UPDATE tasks SET title = ?, done = ? WHERE id = ?',
            (next_title, int(next_done), task_id),
        )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail={'error': 'Task not found'})

    return Task(id=task_id, title=next_title, done=next_done)


@app.delete('/tasks/{task_id}', status_code=status.HTTP_204_NO_CONTENT, summary='Delete task', description='Deletes a task by id from SQLite.')
def delete_task(task_id: int) -> Response:
    with get_db_connection() as connection:
        result = connection.execute('DELETE FROM tasks WHERE id = ?', (task_id,))

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail={'error': 'Task not found'})

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get('/stats', summary='Task stats', description='Returns aggregate counts for all, completed, and open tasks from SQLite.')
def task_stats() -> dict:
    with get_db_connection() as connection:
        row = connection.execute(
            'SELECT COUNT(*) AS total, COALESCE(SUM(done), 0) AS done FROM tasks'
        ).fetchone()
    total = row['total']
    done_count = row['done']
    return {'total': total, 'done': done_count, 'open': total - done_count}


@app.post('/reset', summary='Reset tasks', description='Restores the initial three example tasks in SQLite.')
def reset_tasks() -> list[Task]:
    return reset_database()


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    if isinstance(exc.detail, dict) and 'error' in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={'error': 'request failed'})
