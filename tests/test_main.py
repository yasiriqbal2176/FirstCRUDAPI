"""Unit tests for the Task API, mapped to the W2 CRUD assignment checklist:
full CRUD, status codes (200/201/204/400/404), input validation, the
filter/search/stats/reset extras, and the Swagger/OpenAPI requirement.
"""

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_tasks():
    main.tasks.clear()
    main.tasks.extend(task.model_copy(deep=True) for task in main.seed_tasks)
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
    def test_returns_ok(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}


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

    def test_filter_done_false_excludes_completed_tasks(self, client):
        client.put('/tasks/1', json={'done': True})
        response = client.get('/tasks', params={'done': 'false'})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert all(task['done'] is False for task in body)

    def test_search_is_case_insensitive_substring_match(self, client):
        response = client.get('/tasks', params={'search': 'READ'})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]['title'] == 'Read assignment'

    def test_search_with_no_match_returns_empty_list(self, client):
        response = client.get('/tasks', params={'search': 'nonexistent'})
        assert response.status_code == 200
        assert response.json() == []

    def test_search_blank_after_strip_is_ignored(self, client):
        response = client.get('/tasks', params={'search': '   '})
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_done_and_search_filters_combine(self, client):
        client.put('/tasks/2', json={'done': True})
        response = client.get('/tasks', params={'done': 'true', 'search': 'api'})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]['id'] == 2


class TestGetTask:
    def test_existing_id_returns_task(self, client):
        response = client.get('/tasks/1')
        assert response.status_code == 200
        assert response.json() == {'id': 1, 'title': 'Read assignment', 'done': False}

    def test_unknown_id_returns_404_with_json_error(self, client):
        response = client.get('/tasks/99')
        assert response.status_code == 404
        assert response.json() == {'error': 'Task 99 not found'}


class TestCreateTask:
    def test_valid_title_creates_task_with_201(self, client):
        response = client.post('/tasks', json={'title': 'Buy milk'})
        assert response.status_code == 201
        assert response.json() == {'id': 4, 'title': 'Buy milk', 'done': False}

    def test_created_task_appears_in_list(self, client):
        client.post('/tasks', json={'title': 'Buy milk'})
        response = client.get('/tasks')
        assert len(response.json()) == 4
        assert response.json()[-1]['title'] == 'Buy milk'

    def test_missing_title_returns_400(self, client):
        response = client.post('/tasks', json={})
        assert response.status_code == 400
        assert response.json() == {'error': 'title is required and cannot be empty'}

    def test_empty_title_returns_400(self, client):
        response = client.post('/tasks', json={'title': ''})
        assert response.status_code == 400

    def test_whitespace_only_title_returns_400(self, client):
        response = client.post('/tasks', json={'title': '   '})
        assert response.status_code == 400

    def test_title_is_trimmed(self, client):
        response = client.post('/tasks', json={'title': '  Buy milk  '})
        assert response.status_code == 201
        assert response.json()['title'] == 'Buy milk'

    def test_new_id_reuses_highest_id_after_it_is_deleted(self, client):
        client.delete('/tasks/3')
        response = client.post('/tasks', json={'title': 'Next task'})
        assert response.status_code == 201
        assert response.json()['id'] == 3


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

    def test_update_both_fields(self, client):
        response = client.put('/tasks/1', json={'title': 'Renamed', 'done': True})
        assert response.status_code == 200
        assert response.json() == {'id': 1, 'title': 'Renamed', 'done': True}

    def test_explicit_done_false_is_applied(self, client):
        client.put('/tasks/1', json={'done': True})
        response = client.put('/tasks/1', json={'done': False})
        assert response.status_code == 200
        assert response.json()['done'] is False

    def test_unknown_id_returns_404(self, client):
        response = client.put('/tasks/99', json={'title': 'x'})
        assert response.status_code == 404
        assert response.json() == {'error': 'Task 99 not found'}

    def test_empty_body_returns_400(self, client):
        response = client.put('/tasks/1', json={})
        assert response.status_code == 400
        assert response.json() == {'error': 'request body must include title and/or done'}

    def test_empty_title_returns_400(self, client):
        response = client.put('/tasks/1', json={'title': ''})
        assert response.status_code == 400
        assert response.json() == {'error': 'title cannot be empty'}


class TestDeleteTask:
    def test_delete_existing_task_returns_204_with_empty_body(self, client):
        response = client.delete('/tasks/1')
        assert response.status_code == 204
        assert response.content == b''

    def test_deleted_task_is_gone(self, client):
        client.delete('/tasks/1')
        response = client.get('/tasks/1')
        assert response.status_code == 404

    def test_delete_reduces_task_count(self, client):
        client.delete('/tasks/1')
        response = client.get('/tasks')
        assert len(response.json()) == 2

    def test_unknown_id_returns_404(self, client):
        response = client.delete('/tasks/99')
        assert response.status_code == 404
        assert response.json() == {'error': 'Task 99 not found'}


class TestFullCrudCycle:
    """Mirrors the Stage 4 checkpoint: create, update, complete, delete, confirm."""

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
        assert confirm_response.status_code == 200
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
        client.put('/tasks/2', json={'done': True})

        response = client.post('/reset')
        assert response.status_code == 200
        assert response.json() == [
            {'id': 1, 'title': 'Read assignment', 'done': False},
            {'id': 2, 'title': 'Build API endpoints', 'done': False},
            {'id': 3, 'title': 'Test with Swagger UI', 'done': False},
        ]

        follow_up = client.get('/tasks')
        assert follow_up.json() == response.json()


class TestErrorShape:
    """Every 400/404 in the spec must be a JSON body shaped {"error": "..."}."""

    @pytest.mark.parametrize('method, path, json_body', [
        ('get', '/tasks/99', None),
        ('post', '/tasks', {}),
        ('put', '/tasks/99', {'title': 'x'}),
        ('put', '/tasks/1', {}),
        ('delete', '/tasks/99', None),
    ])
    def test_error_body_has_only_error_key(self, client, method, path, json_body):
        response = client.request(method, path, json=json_body)
        assert response.status_code in (400, 404)
        body = response.json()
        assert list(body.keys()) == ['error']
        assert isinstance(body['error'], str) and body['error']


class TestSwaggerDocs:
    def test_docs_page_is_served(self, client):
        response = client.get('/docs')
        assert response.status_code == 200

    def test_openapi_schema_lists_every_endpoint(self, client):
        response = client.get('/openapi.json')
        assert response.status_code == 200
        paths = response.json()['paths']

        assert 'get' in paths['/']
        assert 'get' in paths['/health']
        assert 'get' in paths['/tasks'] and 'post' in paths['/tasks']
        assert {'get', 'put', 'delete'} <= paths['/tasks/{task_id}'].keys()
        assert 'get' in paths['/stats']
        assert 'post' in paths['/reset']
