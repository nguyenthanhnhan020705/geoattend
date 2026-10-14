from pathlib import Path
import psycopg
from psycopg.rows import dict_row
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
                # Supabase shared pooler user is role.projectref, while SQL
                # grants require the actual PostgreSQL role. Do not guess by
                # splitting dots: valid SQL role names may contain dots.
                with psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=10) as runtime:
                    role = runtime.execute('SELECT current_user AS role').fetchone()['role']
                grant_runtime(conn, role)
        print('Migration hoàn tất: ' + (', '.join(names) or 'không có thay đổi.'))
    except (psycopg.Error, ValueError):
        raise SystemExit('Migration thất bại; kiểm tra quyền database, extension và checksum (không in DSN).')


if __name__ == '__main__':
    main()
