import os
import uuid
from pathlib import Path
import pytest
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.conninfo import make_conninfo, conninfo_to_dict


@pytest.fixture(scope='session')
def test_dsn():
    dsn = os.getenv('GEOATTEND_TEST_DATABASE_URL')
    if not dsn:
        pytest.fail('GEOATTEND_TEST_DATABASE_URL is required for integration tests.')
    parsed = conninfo_to_dict(dsn)
    for name in ('GEOATTEND_DATABASE_URL', 'GEOATTEND_MIGRATION_DATABASE_URL'):
        other = os.getenv(name)
        if other and conninfo_to_dict(other) == parsed:
            pytest.fail('Test DSN must differ from app/migration DSN.')
    name = 'geoattend_test_' + uuid.uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    isolated = make_conninfo(dsn, dbname=name)
    with psycopg.connect(isolated, autocommit=True) as conn:
        conn.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    yield isolated
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))


@pytest.fixture
def db(test_dsn):
    with psycopg.connect(test_dsn, row_factory=dict_row) as conn:
        conn.execute('DROP SCHEMA IF EXISTS geoattend CASCADE')
        conn.commit()
        yield conn
        conn.rollback()


@pytest.fixture
def migrated_db(db):
    from app.db.migrations import apply_migrations
    apply_migrations(db, Path('migrations'))
    return db
