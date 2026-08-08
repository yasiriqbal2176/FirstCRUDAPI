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


def list_tasks() -> list[dict]:
    with get_connection() as connection:
        return connection.execute(
            'SELECT id, title, done FROM tasks ORDER BY id'
        ).fetchall()


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
