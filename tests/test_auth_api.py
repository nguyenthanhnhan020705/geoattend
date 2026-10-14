import pytest

pytestmark = pytest.mark.integration


def signin(client, username='admin', password='Admin1234'):
    return client.post('/api/auth/login',json={'username':username,'password':password})


def test_login_cookie_and_me(api_client, migrated_db):
    response = signin(api_client)
    assert response.status_code == 200
    assert response.json()['role'] == 'ADMIN'
    assert 'password' not in response.text and 'raw_token' not in response.text
    cookie = response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie and 'Path=/' in cookie
    assert api_client.get('/api/auth/me').status_code == 200
    row = migrated_db.execute('SELECT * FROM geoattend.auth_sessions').fetchone()
    assert row['token_hash'] != api_client.cookies.get('geoattend_session')
    assert 43195 <= (row['expires_at'] - row['created_at']).total_seconds() <= 43205
    assert response.headers['cache-control'] == 'no-store'


def test_wrong_unknown_inactive_password_same_response(api_client, migrated_db):
    wrong = signin(api_client,password='wrong1234')
    unknown = signin(api_client,username='unknown',password='wrong1234')
    migrated_db.execute("UPDATE geoattend.profiles SET is_active=false WHERE username='admin'")
    migrated_db.commit()
    inactive = signin(api_client)
    assert wrong.status_code == unknown.status_code == inactive.status_code == 401
    assert wrong.json() == unknown.json() == inactive.json()


def test_attempt_window_expired_and_revoked_sessions(api_client, migrated_db):
    for i in range(5):
        assert signin(api_client,password='wrong1234').status_code == 401
    assert signin(api_client).status_code == 429
    migrated_db.execute("UPDATE geoattend.auth_attempts SET attempted_at=now()-interval '6 minutes'")
    migrated_db.commit()
    assert signin(api_client).status_code == 200
    migrated_db.execute("UPDATE geoattend.auth_sessions SET expires_at=now()-interval '1 second'")
    migrated_db.commit()
    assert api_client.get('/api/auth/me').status_code == 401
    assert signin(api_client).status_code == 200
    migrated_db.execute('UPDATE geoattend.auth_sessions SET revoked_at=now()')
    migrated_db.commit()
    assert api_client.get('/api/auth/me').status_code == 401


def test_csrf_origin_logout_and_redaction(api_client):
    csrf = signin(api_client).json()['csrf_token']
    assert api_client.post('/api/auth/logout').status_code == 403
    assert api_client.post('/api/auth/logout',headers={'X-CSRF-Token':'bad'}).status_code == 403
    assert api_client.post('/api/auth/logout',headers={'X-CSRF-Token':csrf,'Origin':'https://evil.example'}).status_code == 403
    assert api_client.post('/api/auth/logout',headers={'X-CSRF-Token':csrf}).status_code == 204
    assert api_client.get('/api/auth/me').status_code == 401
    assert signin(api_client).status_code == 200
    invalid = api_client.post('/api/auth/login',json={'username':'admin','password':['TopSecret123']})
    assert invalid.status_code == 422 and 'TopSecret123' not in invalid.text
    assert api_client.post('/api/auth/login',json={'username':'admin','password':'Admin1234'},headers={'Origin':'https://evil.example'}).status_code == 403


def test_inactive_account_session_denied(api_client, migrated_db):
    signin(api_client)
    migrated_db.execute("UPDATE geoattend.profiles SET is_active=false WHERE username='admin'")
    migrated_db.commit()
    assert api_client.get('/api/auth/me').status_code == 401
