from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_exact_session_expiry_and_pruning(api_client,migrated_db):
    from app.auth.service import login, resolve_session
    from app.auth.repository import prune_auth_data
    from app.errors import ApiError
    now = datetime(2026,10,14,1,tzinfo=timezone.utc)
    # End any read transaction before service creates the session.
    migrated_db.commit()
    result = login(migrated_db,'admin','Admin1234',now)
    assert resolve_session(migrated_db,result.raw_token,now+timedelta(hours=12,seconds=-1)).account.username == 'admin'
    with pytest.raises(ApiError):
        resolve_session(migrated_db,result.raw_token,now+timedelta(hours=12))
    assert prune_auth_data(migrated_db,now+timedelta(hours=12))[1] == 1


def test_csrf_different_session_and_https_secure(api_client):
    from app.config import Settings
    api_client.app.state.settings = Settings(origin='https://testserver',secure_cookies=True)
    with TestClient(api_client.app,base_url='https://testserver') as first, TestClient(api_client.app,base_url='https://testserver') as second:
        a = first.post('/api/auth/login',json={'username':'admin','password':'Admin1234'})
        b = second.post('/api/auth/login',json={'username':'admin','password':'Admin1234'})
        assert 'Secure' in a.headers['set-cookie']
        assert second.post('/api/auth/logout',headers={'X-CSRF-Token':a.json()['csrf_token']}).status_code == 403
        assert second.post('/api/auth/logout',headers={'X-CSRF-Token':b.json()['csrf_token']}).status_code == 204
        assert first.get('/api/auth/me').status_code == 200


def test_limits_shared_between_app_clients(api_client):
    with TestClient(api_client.app) as other:
        for client in [api_client,other,api_client,other,api_client]:
            assert client.post('/api/auth/login',json={'username':'admin','password':'wrong1234'}).status_code == 401
        assert other.post('/api/auth/login',json={'username':'admin','password':'Admin1234'}).status_code == 429
