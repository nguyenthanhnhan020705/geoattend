from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.test_auth_api import signin

pytestmark = pytest.mark.integration
FRONTEND = 'https://nguyenthanhnhan020705.github.io'


@pytest.fixture
def pages_api(api_client):
    settings = replace(Settings(), frontend_origin=FRONTEND)
    with TestClient(create_app(settings, api_client.app.state.pool)) as client:
        yield client


def token_login(client):
    return client.post('/api/auth/token', headers={'Origin': FRONTEND, 'Sec-Fetch-Site': 'cross-site'},
                       json={'username': 'admin', 'password': 'Admin1234'})


def headers(data):
    return {'Origin': FRONTEND, 'Authorization': 'Bearer ' + data['access_token'],
            'X-CSRF-Token': data['csrf_token'], 'Sec-Fetch-Site': 'cross-site'}


def test_disabled_and_cookie_contract(api_client):
    assert token_login(api_client).status_code == 404
    response = signin(api_client)
    assert 'access_token' not in response.json()
    assert 'HttpOnly' in response.headers['set-cookie']


def test_bearer_login_session_and_revoke(pages_api, migrated_db):
    response = token_login(pages_api)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['token_type'] == 'Bearer' and data['expires_at']
    assert 'set-cookie' not in response.headers
    assert response.headers['cache-control'] == 'no-store'
    assert migrated_db.execute('SELECT token_hash FROM geoattend.auth_sessions').fetchone()['token_hash'] != data['access_token']
    auth = headers(data)
    assert pages_api.get('/api/auth/me', headers=auth).json()['role'] == 'ADMIN'
    assert pages_api.get('/api/attendance/status', headers=auth).status_code == 403
    assert pages_api.post('/api/auth/logout', headers=auth).status_code == 204
    assert pages_api.get('/api/auth/me', headers=auth).status_code == 401


@pytest.mark.parametrize('authorization', ['Bearer invalid', 'Basic bad', 'Bearer', 'Bearer a b', ''])
def test_invalid_bearer_never_falls_back_to_valid_cookie(pages_api, authorization):
    assert signin(pages_api).status_code == 200
    assert pages_api.get('/api/auth/me', headers={'Authorization': authorization, 'Origin': FRONTEND}).status_code == 401


def test_cors_origin_csrf_and_cookie_isolation(pages_api):
    auth = headers(token_login(pages_api).json())
    for origin in ['https://evil.example', FRONTEND + '/geoattend', 'null']:
        assert pages_api.get('/api/auth/me', headers={**auth, 'Origin': origin}).status_code == 403
        assert pages_api.post('/api/auth/token', headers={'Origin': origin}, json={'username':'admin','password':'Admin1234'}).status_code == 403
    missing = {key: value for key, value in auth.items() if key != 'Origin'}
    assert pages_api.get('/api/auth/me', headers=missing).status_code == 403
    assert pages_api.post('/api/auth/logout', headers={**auth, 'X-CSRF-Token': 'wrong'}).status_code == 403
    assert signin(pages_api).status_code == 200
    assert pages_api.post('/api/auth/logout', headers={'Origin':FRONTEND, 'X-CSRF-Token':auth['X-CSRF-Token'], 'Sec-Fetch-Site':'cross-site'}).status_code == 403
    preflight = {'Origin':FRONTEND, 'Access-Control-Request-Method':'PUT',
                 'Access-Control-Request-Headers':'Authorization,Content-Type,X-CSRF-Token,X-Report-Filename'}
    response = pages_api.options('/api/weekly-reports/2026-10-19', headers=preflight)
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == FRONTEND
    assert 'access-control-allow-credentials' not in response.headers
    assert 'access-control-allow-origin' not in pages_api.options('/api/auth/token', headers={**preflight,'Origin':'https://evil.example'}).headers
    pages_api.cookies.clear()
    for method, path, kwargs in [('GET','/api/auth/me',{}), ('POST','/api/auth/token',{'json':{}})]:
        response = pages_api.request(method,path,headers={'Origin':FRONTEND},**kwargs)
        assert response.status_code in (401,422)
        assert response.headers['access-control-allow-origin'] == FRONTEND


def test_expiry_deactivation_password_change(pages_api, migrated_db):
    auth = headers(token_login(pages_api).json())
    migrated_db.execute("UPDATE geoattend.auth_sessions SET expires_at=now()-interval '1 second'")
    migrated_db.commit()
    assert pages_api.get('/api/auth/me',headers=auth).status_code == 401
    auth = headers(token_login(pages_api).json())
    response = pages_api.post('/api/auth/change-password',headers=auth,json={'current_password':'Admin1234','new_password':'NewAdmin1234'})
    assert response.status_code == 204
    assert pages_api.get('/api/auth/me',headers=auth).status_code == 401
    assert token_login(pages_api).status_code == 401


@pytest.mark.parametrize('value', ['https://evil.test/x','https://u:p@evil.test','*','http://evil.test'])
def test_frontend_origin_validation(value):
    with pytest.raises(ValueError):
        replace(Settings(), frontend_origin=value)
