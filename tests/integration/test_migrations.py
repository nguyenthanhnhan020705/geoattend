from pathlib import Path
import pytest

pytestmark = pytest.mark.integration


def test_migrate_all_tables_and_repeat_preserves_data(db):
    from app.db.migrations import apply_migrations
    assert apply_migrations(db, Path('migrations')) == ['001_identity.sql', '002_attendance.sql']
    db.execute("INSERT INTO geoattend.profiles(username,full_name,password_hash,role) VALUES('nhan','Nhân','fixture','USER')")
    db.commit()
    assert apply_migrations(db, Path('migrations')) == []
    assert db.execute('SELECT username FROM geoattend.profiles').fetchone()['username'] == 'nhan'
    tables = {r['table_name'] for r in db.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='geoattend'")}
    assert {'profiles','auth_sessions','auth_attempts','office','attendance_days','work_sessions','attendance_events','office_locations','attendance_requests'} <= tables


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
