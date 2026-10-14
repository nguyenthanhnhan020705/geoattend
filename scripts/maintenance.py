"""Run independently of Uvicorn; each iteration reconciles days and prunes auth."""
import argparse
import time
import psycopg
from psycopg.rows import dict_row
from app import clock
from app.config import Settings
from app.attendance.service import maintain
from app.auth.repository import prune_auth_data
from app.errors import ApiError
from scripts.console import configure_console


def run_once(dsn):
    with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=10) as conn:
        closed = maintain(conn)
        # Separate transaction: cleanup never holds session locks while
        # trying to obtain profile locks used by password changes.
        with conn.transaction():
            attempts,sessions = prune_auth_data(conn,clock.utc_now())
    return closed,attempts,sessions


def main():
    configure_console()
    parser = argparse.ArgumentParser(description='GeoAttend maintenance mỗi phút')
    parser.add_argument('--once',action='store_true')
    args = parser.parse_args()
    dsn = Settings.from_env().database_url
    if not dsn:
        raise SystemExit('Thiếu GEOATTEND_DATABASE_URL.')
    try:
        while True:
            try:
                closed,attempts,sessions = run_once(dsn)
                print(f'Maintenance: đóng {closed} ngày; dọn {attempts} lần thử sai và {sessions} phiên.',flush=True)
            except (psycopg.Error,ApiError):
                print('Maintenance chưa hoàn tất; kiểm tra database và quyền runtime.',flush=True)
                if args.once:
                    raise SystemExit(1)
            if args.once:
                return
            time.sleep(60)
    except KeyboardInterrupt:
        print('Đã dừng maintenance.')


if __name__=='__main__':
    main()
