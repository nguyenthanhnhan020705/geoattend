from app.auth.models import Account
from app.auth.passwords import normalize_username, hash_password, validate_full_name
from app.errors import ApiError
from app.clock import utc_now


def create_initial_admin(conn, username, full_name, password):
    username = normalize_username(username)
    name = validate_full_name(full_name)
    encoded = hash_password(password)
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(174820002)')
        if conn.execute("SELECT id FROM geoattend.profiles WHERE role='ADMIN'").fetchone():
            raise ApiError(409,'ADMIN_EXISTS','Admin đã tồn tại; không tạo thêm hoặc thay mật khẩu.')
        row = conn.execute("INSERT INTO geoattend.profiles(username,full_name,password_hash,role) VALUES(%s,%s,%s,'ADMIN') RETURNING *", (username,name,encoded)).fetchone()
        return Account.from_row(row)


def recover_admin(conn, new_password):
    encoded = hash_password(new_password)
    with conn.transaction():
        row = conn.execute("SELECT id FROM geoattend.profiles WHERE role='ADMIN' FOR UPDATE").fetchone()
        if row is None:
            raise ApiError(404,'ADMIN_NOT_FOUND','Chưa có tài khoản Admin.')
        conn.execute('UPDATE geoattend.profiles SET password_hash=%s WHERE id=%s', (encoded,row['id']))
        conn.execute('UPDATE geoattend.auth_sessions SET revoked_at=%s WHERE user_id=%s AND revoked_at IS NULL', (utc_now(),row['id']))
