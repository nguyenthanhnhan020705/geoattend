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
from datetime import timedelta


@pytest.mark.parametrize('operation',['reset','change'])
def test_expired_session_cleanup_does_not_deadlock_password_change(migrated_db,test_dsn,monkeypatch,operation):
    from app.accounts.service import create_user, reset_user_password, change_password
    from app.auth import service
    from app.errors import ApiError
    user = create_user(migrated_db,'nhan','Nhân','User1234')
    now = datetime.now(timezone.utc)
    migrated_db.execute('INSERT INTO geoattend.auth_sessions(user_id,token_hash,csrf_token,expires_at) VALUES(%s,%s,%s,%s)',(user.id,'expired','fixture',now-timedelta(minutes=1)))
    migrated_db.commit()
    reached_profile = Event()
    original = service.get_account_by_username
    def signal_profile(*args,**kwargs):
        reached_profile.set()
        return original(*args,**kwargs)
    monkeypatch.setattr(service,'get_account_by_username',signal_profile)
    with psycopg.connect(test_dsn,row_factory=dict_row) as reset_conn:
        reset_conn.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE',(user.id,))
        def attempt_login():
            with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
                try:
                    service.login(conn,'nhan','User1234',now)
                    return 'success'
                except ApiError as error:
                    return error.status_code
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(attempt_login)
            assert reached_profile.wait(10)
            try:
                if operation == 'reset':
                    reset_user_password(reset_conn,user.id,'Reset1234',now)
                else:
                    change_password(reset_conn,user.id,'User1234','Reset1234',now)
                reset_conn.commit()
            except BaseException:
                reset_conn.rollback()
                raise
            assert future.result(timeout=15) == 401
