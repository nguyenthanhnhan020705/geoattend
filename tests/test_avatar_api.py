from pathlib import Path
from io import BytesIO
from PIL import Image
import pytest
from tests.test_auth_api import signin
from tests.test_accounts_api import create

pytestmark = pytest.mark.integration
GIF = Path('app/static/images/avatars/default.gif').read_bytes()


def user(client, name):
    headers = {'X-CSRF-Token': signin(client).json()['csrf_token']}
    assert create(client, headers, name).status_code == 201
    return {'X-CSRF-Token': signin(client, name, 'User1234').json()['csrf_token'], 'Content-Type': 'image/gif'}


def test_avatar_persistence_isolation_and_validation(api_client):
    headers = user(api_client, 'avatarone')
    assert api_client.get('/api/account/avatar').status_code == 204
    assert api_client.put('/api/account/avatar', content=GIF, headers={'Content-Type': 'image/gif'}).status_code == 403
    assert api_client.put('/api/account/avatar', content=GIF, headers=headers).status_code == 204
    signin(api_client, 'avatarone', 'User1234')
    saved = api_client.get('/api/account/avatar')
    assert saved.status_code == 200 and saved.content == GIF
    assert saved.headers['content-type'] == 'image/gif'
    assert saved.headers['cache-control'] == 'no-store'
    headers['X-CSRF-Token'] = api_client.get('/api/auth/me').json()['csrf_token']
    assert api_client.put('/api/account/avatar', content=b'<svg>bad</svg>', headers=headers).status_code == 422
    assert api_client.put('/api/account/avatar', content=GIF[:30], headers=headers).status_code == 422
    assert api_client.put('/api/account/avatar', content=b'x' * 5_000_001, headers=headers).status_code == 413
    assert api_client.get('/api/account/avatar').content == GIF
    png = BytesIO()
    Image.new('RGB', (24,24), 'red').save(png, format='PNG')
    assert api_client.put('/api/account/avatar', content=png.getvalue(), headers=headers).status_code == 204
    assert api_client.get('/api/account/avatar').content == png.getvalue()
    user(api_client, 'avatartwo')
    assert api_client.get('/api/account/avatar').status_code == 204
    signin(api_client)
    assert api_client.get('/api/account/avatar').status_code == 403


def test_avatar_requires_login(api_client):
    assert api_client.get('/api/account/avatar').status_code == 401
    assert api_client.put('/api/account/avatar', content=GIF).status_code == 401
