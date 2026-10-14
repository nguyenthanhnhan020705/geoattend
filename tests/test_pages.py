import pytest
from tests.test_auth_api import signin

pytestmark = pytest.mark.integration


def test_anonymous_user_page_redirect(api_client):
    response = api_client.get('/user',follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/login'


def test_admin_pages_no_user_attendance(api_client):
    signin(api_client)
    assert api_client.get('/admin/users').status_code == 200
    assert api_client.get('/account').status_code == 200
    assert api_client.get('/user').status_code == 403


def test_user_cannot_open_admin_page(api_client):
    csrf = signin(api_client).json()['csrf_token']
    api_client.post('/api/admin/users',headers={'X-CSRF-Token':csrf},json={'username':'nhan','full_name':'Nhân','password':'User1234'})
    signin(api_client,'nhan','User1234')
    assert api_client.get('/user').status_code == 200
    assert api_client.get('/account').status_code == 200
    assert api_client.get('/admin/users').status_code == 403
