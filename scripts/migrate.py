from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from psycopg.conninfo import conninfo_to_dict
from app.config import Settings
from app.db.migrations import apply_migrations, grant_runtime
from scripts.console import configure_console


def main():
    configure_console()
    settings = Settings.from_env()
    if not settings.migration_database_url:
        raise SystemExit('Thiếu GEOATTEND_MIGRATION_DATABASE_URL.')
    try:
        with psycopg.connect(settings.migration_database_url, row_factory=dict_row) as conn:
            names = apply_migrations(conn, Path(__file__).resolve().parents[1]/'migrations')
            if settings.database_url:
                role = conninfo_to_dict(settings.database_url).get('user')
                if not role:
                    raise ValueError('Runtime DSN phải có user.')
                grant_runtime(conn, role)
        print('Migration hoàn tất: ' + (', '.join(names) or 'không có thay đổi.'))
    except (psycopg.Error, ValueError):
        raise SystemExit('Migration thất bại; kiểm tra quyền database, extension và checksum (không in DSN).')


if __name__ == '__main__':
    main()
