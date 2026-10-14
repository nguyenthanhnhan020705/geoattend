from uuid import uuid4
from fastapi.testclient import TestClient
import pytest
from tests.test_auth_api import signin

pytestmark = pytest.mark.integration


def create(client, headers, username='nhan'):
    return client.post('/api/admin/users',headers=headers,json={'username':username,'full_name':'Nguyễn Thành Nhân','password':'User1234'})


@pytest.fixture
def account_setup(api_client):
    headers = {'X-CSRF-Token':signin(api_client).json()['csrf_token']}
    response = create(api_client,headers)
    assert response.status_code == 201
    return headers, response.json()['id']


def test_create_list_permissions_and_duplicate(api_client):
    assert api_client.get('/api/admin/users').status_code == 401
    headers = {'X-CSRF-Token':signin(api_client).json()['csrf_token']}
    assert create(api_client,{}).status_code == 403
    response = create(api_client,headers,' Nhan ')
    assert response.status_code == 201
    assert response.json()['username'] == 'nhan' and response.json()['role'] == 'USER'
    assert 'password' not in response.text
    assert create(api_client,headers,'NHAN').status_code == 409
    invalid = api_client.post('/api/admin/users',headers=headers,json={'username':'evil','full_name':'Evil','password':'Password123','role':'ADMIN'})
    assert invalid.status_code == 422 and 'Password123' not in invalid.text
    assert len(api_client.get('/api/admin/users').json()['items']) == 1
    signin(api_client,'nhan','User1234')
    assert api_client.get('/api/admin/users').status_code == 403
    assert create(api_client,{'X-CSRF-Token':api_client.get('/api/auth/me').json()['csrf_token']},'other').status_code == 403


def test_reset_revokes_all_user_sessions_not_admin(api_client,account_setup,migrated_db):
    headers, user_id = account_setup
    with TestClient(api_client.app) as user1, TestClient(api_client.app) as user2:
        assert signin(user1,'nhan','User1234').status_code == 200
        assert signin(user2,'nhan','User1234').status_code == 200
        day = migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,'2026-10-14','CHECKED_OUT') RETURNING id", (user_id,)).fetchone()['id']
        migrated_db.execute("INSERT INTO geoattend.attendance_events(day_id,event_type,event_time,source) VALUES(%s,'DAY_END',now(),'SYSTEM')", (day,))
        migrated_db.commit()
        assert api_client.post(f'/api/admin/users/{user_id}/reset-password',headers=headers,json={'new_password':'Reset1234'}).status_code == 204
        assert user1.get('/api/auth/me').status_code == user2.get('/api/auth/me').status_code == 401
        assert api_client.get('/api/auth/me').status_code == 200
        assert signin(user1,'nhan','User1234').status_code == 401
        assert signin(user1,'nhan','Reset1234').status_code == 200
        assert user1.get('/api/auth/me').json()['role'] == 'USER'
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_events').fetchone()['n'] == 1


def test_change_password_validates_and_revokes(api_client,account_setup):
    _, user_id = account_setup
    with TestClient(api_client.app) as user1, TestClient(api_client.app) as user2:
        csrf = signin(user1,'nhan','User1234').json()['csrf_token']
        signin(user2,'nhan','User1234')
        headers = {'X-CSRF-Token':csrf}
        assert user1.post('/api/auth/change-password',headers=headers,json={'current_password':'Wrong1234','new_password':'Changed123'}).status_code == 401
        assert user1.get('/api/auth/me').status_code == 200
        assert user1.post('/api/auth/change-password',headers=headers,json={'current_password':'User1234','new_password':'short'}).status_code == 422
        assert user1.post('/api/auth/change-password',headers=headers,json={'current_password':'User1234','new_password':'Changed123'}).status_code == 204
        assert user1.get('/api/auth/me').status_code == user2.get('/api/auth/me').status_code == 401
        assert signin(user1,'nhan','User1234').status_code == 401
        assert signin(user1,'nhan','Changed123').status_code == 200
        assert user1.get('/api/auth/me').json()['id'] == user_id


def test_admin_reset_target_restrictions(api_client,account_setup):
    headers, user_id = account_setup
    admin_id = api_client.get('/api/auth/me').json()['id']
    assert api_client.post(f'/api/admin/users/{admin_id}/reset-password',headers=headers,json={'new_password':'Reset1234'}).status_code == 403
    assert api_client.post(f'/api/admin/users/{uuid4()}/reset-password',headers=headers,json={'new_password':'Reset1234'}).status_code == 404
