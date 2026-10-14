import pytest
import psycopg

pytestmark = pytest.mark.integration


def insert(conn, username, role='USER'):
    return conn.execute('INSERT INTO geoattend.profiles(username,full_name,password_hash,role) VALUES(%s,%s,%s,%s) RETURNING id', (username,'Nhân','fixture',role)).fetchone()['id']


def test_database_rejects_second_admin(migrated_db):
    insert(migrated_db,'admin','ADMIN')
    with pytest.raises(psycopg.errors.UniqueViolation):
        with migrated_db.transaction():
            insert(migrated_db,'admin2','ADMIN')


def test_duplicate_normalized_username_rejected(migrated_db):
    insert(migrated_db,'nhan')
    with pytest.raises(psycopg.Error):
        with migrated_db.transaction():
            insert(migrated_db,'NHAN')
    with pytest.raises(psycopg.errors.UniqueViolation):
        with migrated_db.transaction():
            insert(migrated_db,'nhan')


def test_work_session_and_office_constraints(migrated_db):
    user = insert(migrated_db,'nhan')
    day = migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,'2026-10-14','WORKING_REMOTE') RETURNING id",(user,)).fetchone()['id']
    migrated_db.execute("INSERT INTO geoattend.work_sessions(day_id,work_mode,start_time) VALUES(%s,'REMOTE',now())", (day,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        with migrated_db.transaction():
            migrated_db.execute("INSERT INTO geoattend.work_sessions(day_id,work_mode,start_time) VALUES(%s,'REMOTE',now())", (day,))
    migrated_db.execute("INSERT INTO geoattend.office(name,address) VALUES('Office','HCM')")
    with pytest.raises(psycopg.errors.UniqueViolation):
        with migrated_db.transaction():
            migrated_db.execute("INSERT INTO geoattend.office(name,address) VALUES('Other','HCM')")
import secrets
import uuid


def test_runtime_has_dml_but_no_ddl(migrated_db, test_dsn):
    from app.db.migrations import grant_runtime
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    role = 'test_runtime_' + uuid.uuid4().hex
    password = secrets.token_urlsafe(24)
    migrated_db.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role), sql.Literal(password)))
    grant_runtime(migrated_db, role)
    migrated_db.commit()
    try:
        with psycopg.connect(make_conninfo(test_dsn, user=role, password=password)) as conn:
            conn.execute("INSERT INTO geoattend.profiles(username,full_name,password_hash,role) VALUES('worker','Nhân','fixture','USER')")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute('ALTER TABLE geoattend.profiles ADD COLUMN forbidden int')
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute('DELETE FROM geoattend.profiles')
    finally:
        migrated_db.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
        migrated_db.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
        migrated_db.commit()
