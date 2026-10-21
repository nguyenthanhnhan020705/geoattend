import psycopg
from psycopg.rows import dict_row
from app.auth.repository import prune_auth_data
from app.clock import utc_now
from app.config import Settings
from scripts.console import configure_console


def main():
    configure_console()
    dsn = Settings.from_env().database_url
    if not dsn:
        raise SystemExit('Thiếu GEOATTEND_DATABASE_URL.')
    try:
        with psycopg.connect(dsn,row_factory=dict_row) as conn:
            attempts, sessions = prune_auth_data(conn,utc_now())
        print(f'Đã dọn {attempts} lần thử sai hết hạn và {sessions} phiên đăng nhập không còn hiệu lực.')
    except psycopg.Error:
        raise SystemExit('Không thể dọn dữ liệu xác thực; kiểm tra database và quyền runtime.')


if __name__ == '__main__':
    main()
