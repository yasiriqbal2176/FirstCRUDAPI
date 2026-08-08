"""Unit tests for the Task API, run against a real Postgres instance.

Start the database before running these (either the Stage 0 standalone
container, or `docker compose up -d db`), then:

    pip install -r requirements-dev.txt
    pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_tasks():
    import repository
    repository.reset_tasks()
    yield


class TestRoot:
    def test_returns_api_metadata(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert response.json() == {
            'name': 'Task API',
            'version': '1.0',
            'endpoints': ['/tasks'],
        }


class TestHealth:
    def test_reports_db_ok(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok', 'db': 'ok'}


class TestListTasks:
    def test_returns_all_seed_tasks(self, client):
        response = client.get('/tasks')
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 3
        assert [task['id'] for task in body] == [1, 2, 3]

    def test_filter_done_true_excludes_open_tasks(self, client):
        client.put('/tasks/1', json={'done': True})
        response = client.get('/tasks', params={'done': 'true'})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]['id'] == 1

    def test_search_is_case_insensitive_substring_match(self, client):
        response = client.get('/tasks', params={'search': 'read'})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]['title'] == 'Read assignment'

    def test_search_with_no_match_returns_empty_list(self, client):
        response = client.get('/tasks', params={'search': 'nonexistent'})
        assert response.status_code == 200
        assert response.json() == []


class TestGetTask:
    def test_existing_id_returns_task(self, client):
        response = client.get('/tasks/1')
        assert response.status_code == 200
        assert response.json() == {'id': 1, 'title': 'Read assignment', 'done': False}

    def test_unknown_id_returns_404_with_json_error(self, client):
        response = client.get('/tasks/999')
        assert response.status_code == 404
        assert response.json() == {'error': 'Task not found'}


class TestCreateTask:
    def test_valid_title_creates_task_with_201(self, client):
        response = client.post('/tasks', json={'title': 'Buy milk'})
        assert response.status_code == 201
        body = response.json()
        assert body['title'] == 'Buy milk'
        assert body['done'] is False
        assert body['id'] == 4

    def test_created_task_appears_in_list(self, client):
        client.post('/tasks', json={'title': 'Buy milk'})
        response = client.get('/tasks')
        assert len(response.json()) == 4

    def test_missing_title_returns_400(self, client):
        response = client.post('/tasks', json={})
        assert response.status_code == 400
        assert response.json() == {'error': 'title is required and cannot be empty'}

    def test_empty_title_returns_400(self, client):
        response = client.post('/tasks', json={'title': '   '})
        assert response.status_code == 400

    def test_title_is_trimmed(self, client):
        response = client.post('/tasks', json={'title': '  Buy milk  '})
        assert response.status_code == 201
        assert response.json()['title'] == 'Buy milk'


class TestUpdateTask:
    def test_update_title_only_leaves_done_unchanged(self, client):
        response = client.put('/tasks/1', json={'title': 'Read the whole assignment'})
        assert response.status_code == 200
        body = response.json()
        assert body['title'] == 'Read the whole assignment'
        assert body['done'] is False

    def test_update_done_only_leaves_title_unchanged(self, client):
        response = client.put('/tasks/1', json={'done': True})
        assert response.status_code == 200
        body = response.json()
        assert body['title'] == 'Read assignment'
        assert body['done'] is True

    def test_unknown_id_returns_404(self, client):
        response = client.put('/tasks/999', json={'title': 'x'})
        assert response.status_code == 404
        assert response.json() == {'error': 'Task not found'}

    def test_empty_body_returns_400(self, client):
        response = client.put('/tasks/1', json={})
        assert response.status_code == 400
        assert response.json() == {'error': 'request body must include title and/or done'}


class TestDeleteTask:
    def test_delete_existing_task_returns_204_with_empty_body(self, client):
        response = client.delete('/tasks/1')
        assert response.status_code == 204
        assert response.content == b''

    def test_deleted_task_is_gone(self, client):
        client.delete('/tasks/1')
        response = client.get('/tasks/1')
        assert response.status_code == 404

    def test_unknown_id_returns_404(self, client):
        response = client.delete('/tasks/999')
        assert response.status_code == 404
        assert response.json() == {'error': 'Task not found'}


class TestFullCrudCycle:
    """Mirrors the Stage 3 checkpoint: create, complete, delete, confirm."""

    def test_create_update_complete_delete_confirm(self, client):
        create_response = client.post('/tasks', json={'title': 'Ship feature'})
        assert create_response.status_code == 201
        task_id = create_response.json()['id']

        update_response = client.put(f'/tasks/{task_id}', json={'done': True})
        assert update_response.status_code == 200
        assert update_response.json()['done'] is True

        delete_response = client.delete(f'/tasks/{task_id}')
        assert delete_response.status_code == 204

        confirm_response = client.get('/tasks')
        assert task_id not in [task['id'] for task in confirm_response.json()]


class TestStats:
    def test_initial_counts(self, client):
        response = client.get('/stats')
        assert response.status_code == 200
        assert response.json() == {'total': 3, 'done': 0, 'open': 3}

    def test_counts_after_changes(self, client):
        client.put('/tasks/1', json={'done': True})
        client.post('/tasks', json={'title': 'Extra task'})
        response = client.get('/stats')
        assert response.json() == {'total': 4, 'done': 1, 'open': 3}


class TestReset:
    def test_restores_seed_tasks_after_mutation(self, client):
        client.post('/tasks', json={'title': 'Temporary'})
        client.delete('/tasks/1')

        response = client.post('/reset')
        assert response.status_code == 200
        assert response.json() == [
            {'id': 1, 'title': 'Read assignment', 'done': False},
            {'id': 2, 'title': 'Build API endpoints', 'done': False},
            {'id': 3, 'title': 'Test with Swagger UI', 'done': False},
        ]


class TestErrorShape:
    """Every 400/404 in the spec must be a JSON body shaped {"error": "..."}."""

    @pytest.mark.parametrize('method, path, json_body', [
        ('get', '/tasks/999', None),
        ('post', '/tasks', {}),
        ('put', '/tasks/999', {'title': 'x'}),
        ('put', '/tasks/1', {}),
        ('delete', '/tasks/999', None),
    ])
    def test_error_body_has_only_error_key(self, client, method, path, json_body):
        response = client.request(method, path, json=json_body)
        assert response.status_code in (400, 404)
        body = response.json()
        assert list(body.keys()) == ['error']
        assert isinstance(body['error'], str) and body['error']
