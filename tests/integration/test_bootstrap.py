from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import pytest
import psycopg
from psycopg.rows import dict_row

pytestmark = pytest.mark.integration


def test_bootstrap_repeat_and_recovery(migrated_db):
    from app.accounts.bootstrap import create_initial_admin, recover_admin
    from app.auth.passwords import verify_password
    from app.errors import ApiError
    admin = create_initial_admin(migrated_db,'Admin','Quản lý','Initial123')
    migrated_db.commit()
    with pytest.raises(ApiError):
        with migrated_db.transaction():
            create_initial_admin(migrated_db,'Other','Khác','Other1234')
    row = migrated_db.execute('SELECT * FROM geoattend.profiles WHERE id=%s', (admin.id,)).fetchone()
    assert row['username'] == 'admin'
    assert verify_password(row['password_hash'],'Initial123')
    migrated_db.execute('INSERT INTO geoattend.auth_sessions(user_id,token_hash,csrf_token,expires_at) VALUES(%s,%s,%s,%s)', (admin.id,'fixture','csrf',datetime.now(timezone.utc)+timedelta(hours=1)))
    recover_admin(migrated_db,'Recovered123')
    row = migrated_db.execute('SELECT * FROM geoattend.profiles WHERE id=%s', (admin.id,)).fetchone()
    assert verify_password(row['password_hash'],'Recovered123')
    assert migrated_db.execute('SELECT revoked_at FROM geoattend.auth_sessions').fetchone()['revoked_at'] is not None


def test_concurrent_bootstrap_creates_one_admin(migrated_db, test_dsn):
    from app.accounts.bootstrap import create_initial_admin
    from app.errors import ApiError
    migrated_db.commit()
    def attempt(n):
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            try:
                create_initial_admin(conn,'admin'+str(n),'Admin','Password123')
                return True
            except ApiError:
                return False
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sum(executor.map(attempt,[1,2])) == 1
    assert migrated_db.execute("SELECT count(*) AS n FROM geoattend.profiles WHERE role='ADMIN'").fetchone()['n'] == 1


def test_cli_bootstrap_confirmation_and_repeat(migrated_db, test_dsn, monkeypatch, capsys):
    from scripts import bootstrap_admin
    monkeypatch.setenv('GEOATTEND_MIGRATION_DATABASE_URL',test_dsn)
    answers = iter(['admin','Quản lý'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(answers))
    passwords = iter(['Password123','Mismatch123'])
    monkeypatch.setattr(bootstrap_admin,'getpass',lambda prompt:next(passwords))
    with pytest.raises(SystemExit):
        bootstrap_admin.main()
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.profiles').fetchone()['n'] == 0
    migrated_db.commit()
    answers = iter(['admin','Quản lý','other','Khác'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(answers))
    monkeypatch.setattr(bootstrap_admin,'getpass',lambda prompt:'Password123')
    bootstrap_admin.main()
    with pytest.raises(SystemExit):
        bootstrap_admin.main()
    assert 'Password123' not in capsys.readouterr().out
