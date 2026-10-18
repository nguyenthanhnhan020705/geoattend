from pathlib import Path
import pytest

pytestmark = pytest.mark.integration


def test_migrate_all_tables_and_repeat_preserves_data(db):
    from app.db.migrations import apply_migrations
    assert apply_migrations(db, Path('migrations')) == ['001_identity.sql', '002_attendance.sql', '003_attendance_replay.sql', '004_history_deletion.sql', '005_weekly_reports.sql']
    db.execute("INSERT INTO geoattend.profiles(username,full_name,password_hash,role) VALUES('nhan','Nhân','fixture','USER')")
    db.commit()
    assert apply_migrations(db, Path('migrations')) == []
    assert db.execute('SELECT username FROM geoattend.profiles').fetchone()['username'] == 'nhan'
    tables = {r['table_name'] for r in db.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='geoattend'")}
    assert {'profiles','auth_sessions','auth_attempts','office','attendance_days','work_sessions','attendance_events','office_locations','attendance_requests','weekly_reports'} <= tables


def test_checksum_and_failed_migration(db, tmp_path):
    from app.db.migrations import apply_migrations
    (tmp_path/'001_fixture.sql').write_text('CREATE TABLE geoattend.fixture(id int);')
    apply_migrations(db, tmp_path)
    (tmp_path/'001_fixture.sql').write_text('CREATE TABLE geoattend.fixture(id bigint);')
    with pytest.raises(ValueError):
        apply_migrations(db, tmp_path)
    (tmp_path/'001_fixture.sql').write_text('CREATE TABLE geoattend.fixture(id int);')
    (tmp_path/'002_broken.sql').write_text('INVALID SQL;')
    import psycopg
    with pytest.raises(psycopg.Error):
        apply_migrations(db, tmp_path)
    assert db.execute('SELECT count(*) AS n FROM geoattend.schema_migrations').fetchone()['n'] == 1
import os
import subprocess
import sys


def test_migration_cli_unicode_output(test_dsn):
    env = os.environ.copy()
    env['GEOATTEND_MIGRATION_DATABASE_URL'] = test_dsn
    env['PYTHONIOENCODING'] = 'cp1252'
    env.pop('GEOATTEND_DATABASE_URL', None)
    result = subprocess.run([sys.executable,'-m','scripts.migrate'],env=env,capture_output=True,encoding='utf-8')
    assert result.returncode == 0, result.stderr
    assert 'Migration hoàn tất' in result.stdout


def test_migration_grants_actual_runtime_role_through_local_launcher(db,test_dsn,tmp_path,monkeypatch):
    from uuid import uuid4
    from psycopg import sql
    from psycopg.conninfo import make_conninfo,conninfo_to_dict
    import psycopg
    from scripts.local_run import local_environment
    from scripts import migrate
    role='launcher_runtime_'+uuid4().hex
    db.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    db.commit()
    # Simulate only shared pooler routing. Both administrative and runtime
    # connections/queries/grants still run on the real isolated PostgreSQL.
    routed=make_conninfo(test_dsn,user=role+'.projectref')
    path=tmp_path/'.env'
    path.write_text('GEOATTEND_MIGRATION_DATABASE_URL='+test_dsn+'\nGEOATTEND_DATABASE_URL='+routed+'\n',encoding='utf-8')
    env=local_environment(path,'migrate',{})
    for key in ('GEOATTEND_MIGRATION_DATABASE_URL','GEOATTEND_DATABASE_URL'):
        monkeypatch.setenv(key,env.get(key,''))
    connect=psycopg.connect
    def pooler_transport(dsn,*args,**kwargs):
        if conninfo_to_dict(dsn).get('user')==role+'.projectref':
            dsn=make_conninfo(dsn,user=role)
        return connect(dsn,*args,**kwargs)
    monkeypatch.setattr(psycopg,'connect',pooler_transport)
    try:
        migrate.main()
        with connect(make_conninfo(test_dsn,user=role)) as runtime:
            runtime.execute('SELECT id FROM geoattend.profiles').fetchall()
            runtime.execute('SELECT id FROM geoattend.attendance_requests').fetchall()
    finally:
        db.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
        db.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
        db.commit()
