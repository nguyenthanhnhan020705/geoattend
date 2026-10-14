from getpass import getpass
import psycopg
from psycopg.rows import dict_row
from app.accounts.bootstrap import recover_admin
from app.config import Settings
from app.errors import ApiError
from scripts.console import configure_console


def main():
    configure_console()
    dsn = Settings.from_env().migration_database_url
    if not dsn:
        raise SystemExit('Thiếu GEOATTEND_MIGRATION_DATABASE_URL.')
    try:
        with psycopg.connect(dsn,row_factory=dict_row) as conn:
            row = conn.execute("SELECT username FROM geoattend.profiles WHERE role='ADMIN'").fetchone()
            if not row or input('Nhập tên Admin để xác nhận khôi phục: ').strip().lower() != row['username']:
                raise SystemExit('Xác nhận tài khoản không khớp.')
            password = getpass('Mật khẩu mới: ')
            if password != getpass('Nhập lại mật khẩu mới: '):
                raise SystemExit('Mật khẩu xác nhận không khớp.')
            recover_admin(conn,password)
        print('Đã đặt lại mật khẩu Admin và thu hồi các phiên đăng nhập.')
    except ApiError as error:
        raise SystemExit(error.message)
    except psycopg.Error:
        raise SystemExit('Không thể khôi phục Admin; kiểm tra database và quyền quản trị.')


if __name__ == '__main__':
    main()
