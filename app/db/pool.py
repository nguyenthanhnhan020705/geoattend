from contextlib import contextmanager
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def make_pool(dsn):
    return ConnectionPool(dsn, min_size=0, max_size=5, open=False,
                          kwargs={'row_factory': dict_row, 'connect_timeout': 3}, timeout=4)


@contextmanager
def transaction(pool):
    with pool.connection() as conn:
        with conn.transaction():
            yield conn
