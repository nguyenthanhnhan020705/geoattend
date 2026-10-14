def test_health_ready(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'database': 'ok'}


def test_health_unavailable_does_not_leak_dsn():
    from conftest import HealthPool
    from app.main import create_app
    from app.config import Settings
    from fastapi.testclient import TestClient
    with TestClient(create_app(Settings(), HealthPool(True))) as client:
        response = client.get('/api/health')
        assert response.status_code == 503
        assert 'secret-dsn' not in response.text


def test_login_html_and_unknown_api(client):
    assert 'text/html' in client.get('/login').headers['content-type']
    response = client.get('/api/unknown')
    assert response.status_code == 404
    assert response.headers['content-type'].startswith('application/json')
