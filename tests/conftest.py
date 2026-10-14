from contextlib import contextmanager
import pytest

pytest_plugins = ['tests.db_fixtures']


@pytest.fixture
def api_client(migrated_db, test_dsn):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.config import Settings
    from app.db.pool import make_pool
    from app.accounts.bootstrap import create_initial_admin
    create_initial_admin(migrated_db,'admin','Quản lý','Admin1234')
    migrated_db.commit()
    pool = make_pool(test_dsn)
    pool.open()
    with TestClient(create_app(Settings(),pool)) as client:
        yield client
    pool.close()


class HealthPool:
    def __init__(self, unavailable=False):
        self.unavailable = unavailable

    @contextmanager
    def connection(self):
        if self.unavailable:
            import psycopg
            raise psycopg.OperationalError("secret-dsn")
        yield self

    def execute(self, query):
        assert query == "SELECT 1"
        return self

    def fetchone(self):
        return {"?column?": 1}


@pytest.fixture
def client():
    from app.main import create_app
    from app.config import Settings
    from fastapi.testclient import TestClient
    with TestClient(create_app(Settings(), HealthPool())) as client:
        yield client
