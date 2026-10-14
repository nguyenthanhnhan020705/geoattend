from datetime import datetime, timezone
import pytest

pytestmark = pytest.mark.integration


def test_change_invalid_current_leaves_sessions_and_identity(api_client,migrated_db):
    from app.accounts.service import change_password
    from app.errors import ApiError
    from tests.test_auth_api import signin
    logged = signin(api_client)
    account = logged.json()
    with pytest.raises(ApiError):
        with migrated_db.transaction():
            change_password(migrated_db,account['id'],'wrong1234','Different123',datetime.now(timezone.utc))
    row = migrated_db.execute('SELECT username,role,full_name FROM geoattend.profiles WHERE id=%s',(account['id'],)).fetchone()
    assert row == {'username':'admin','role':'ADMIN','full_name':'Quản lý'}
    assert api_client.get('/api/auth/me').status_code == 200
