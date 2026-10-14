from concurrent.futures import ThreadPoolExecutor
from threading import Event
from datetime import datetime, timezone
import pytest
import psycopg
from psycopg.rows import dict_row

pytestmark = pytest.mark.integration


def test_login_before_reset_session_is_revoked(migrated_db,test_dsn,monkeypatch):
    from app.accounts.service import create_user, reset_user_password
    from app.auth import service
    from app.errors import ApiError
    user = create_user(migrated_db,'nhan','Nhân','User1234')
    migrated_db.commit()
    verified, release = Event(), Event()
    original = service.verify_password
    def held_verify(encoded, password):
        valid = original(encoded,password)
        if password == 'User1234':
            verified.set()
            assert release.wait(10)
        return valid
    monkeypatch.setattr(service,'verify_password',held_verify)
    def logging_in():
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            return service.login(conn,'nhan','User1234',datetime.now(timezone.utc))
    def resetting():
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            reset_user_password(conn,user.id,'Reset1234',datetime.now(timezone.utc))
    with ThreadPoolExecutor(max_workers=2) as executor:
        login_future = executor.submit(logging_in)
        assert verified.wait(10)
        reset_future = executor.submit(resetting)
        release.set()
        result = login_future.result(timeout=15)
        reset_future.result(timeout=15)
    with pytest.raises(ApiError):
        service.resolve_session(migrated_db,result.raw_token,datetime.now(timezone.utc))


def test_concurrent_create_same_username_one_success(migrated_db,test_dsn):
    from app.accounts.service import create_user
    from app.errors import ApiError
    migrated_db.commit()
    def attempt(username):
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            try:
                create_user(conn,username,'Nhân','User1234')
                return True
            except ApiError:
                return False
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sum(executor.map(attempt,['Nhan',' nhan '])) == 1
