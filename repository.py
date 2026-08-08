"""The only module that talks to Postgres. Routes never touch SQL directly."""

import os

import psycopg
from psycopg.rows import dict_row

SEED_TASKS = [
    ('Read assignment', False),
    ('Build API endpoints', False),
    ('Test with Swagger UI', False),
]

CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT FALSE
)
'''


def get_connection() -> psycopg.Connection:
    database_url = os.environ['DATABASE_URL']
    return psycopg.connect(database_url, row_factory=dict_row)


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(CREATE_TABLE_SQL)
        count = connection.execute('SELECT COUNT(*) AS count FROM tasks').fetchone()['count']
        if count == 0:
            connection.executemany(
                'INSERT INTO tasks (title, done) VALUES (%s, %s)',
                SEED_TASKS,
            )


def ping() -> bool:
    with get_connection() as connection:
        connection.execute('SELECT 1')
    return True


def list_tasks(done: bool | None = None, search: str | None = None) -> list[dict]:
    query = 'SELECT id, title, done FROM tasks'
    conditions: list[str] = []
    parameters: list[object] = []

    if done is not None:
        conditions.append('done = %s')
        parameters.append(done)

    if search:
        conditions.append('title ILIKE %s')
        parameters.append(f'%{search}%')

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY id'

    with get_connection() as connection:
        return connection.execute(query, parameters).fetchall()


def get_task(task_id: int) -> dict | None:
    with get_connection() as connection:
        return connection.execute(
            'SELECT id, title, done FROM tasks WHERE id = %s',
            (task_id,),
        ).fetchone()


def create_task(title: str) -> dict:
    with get_connection() as connection:
        return connection.execute(
            'INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done',
            (title, False),
        ).fetchone()


def update_task(task_id: int, title: str, done: bool) -> dict | None:
    with get_connection() as connection:
        return connection.execute(
            'UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done',
            (title, done, task_id),
        ).fetchone()


def delete_task(task_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
        return cursor.rowcount > 0


def task_stats() -> dict:
    with get_connection() as connection:
        row = connection.execute(
            'SELECT COUNT(*) AS total, COALESCE(SUM(done::int), 0) AS done FROM tasks'
        ).fetchone()
    total = row['total']
    done_count = row['done']
    return {'total': total, 'done': done_count, 'open': total - done_count}


def reset_tasks() -> list[dict]:
    with get_connection() as connection:
        connection.execute('DELETE FROM tasks')
        connection.execute('ALTER SEQUENCE tasks_id_seq RESTART WITH 1')
        connection.executemany(
            'INSERT INTO tasks (title, done) VALUES (%s, %s)',
            SEED_TASKS,
        )
        return connection.execute(
            'SELECT id, title, done FROM tasks ORDER BY id'
        ).fetchall()
