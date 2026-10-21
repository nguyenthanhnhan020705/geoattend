from getpass import getpass
import psycopg
from psycopg.rows import dict_row
from app.accounts.bootstrap import create_initial_admin
from app.config import Settings
from app.errors import ApiError
from scripts.console import configure_console


def main():
    configure_console()
    dsn = Settings.from_env().migration_database_url
    if not dsn:
        raise SystemExit('Thiếu GEOATTEND_MIGRATION_DATABASE_URL.')
    username = input('Tên tài khoản Admin: ')
    name = input('Họ tên: ')
    password = getpass('Mật khẩu: ')
    if password != getpass('Nhập lại mật khẩu: '):
        raise SystemExit('Mật khẩu xác nhận không khớp.')
    try:
        with psycopg.connect(dsn,row_factory=dict_row) as conn:
            create_initial_admin(conn,username,name,password)
        print('Đã khởi tạo Admin.')
    except ApiError as error:
        raise SystemExit(error.message)
    except psycopg.Error:
        raise SystemExit('Không thể khởi tạo Admin; kiểm tra database và quyền quản trị.')


if __name__ == '__main__':
    main()
