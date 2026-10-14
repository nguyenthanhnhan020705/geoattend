from contextlib import contextmanager
import pytest


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
