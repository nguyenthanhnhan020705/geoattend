from psycopg.errors import UniqueViolation
from app.accounts.repository import get_account_by_id
from app.auth.models import Account
from app.auth.passwords import normalize_username, hash_password, verify_password, validate_full_name
from app.auth.repository import revoke_all
from app.errors import ApiError


def create_user(conn, username, full_name, password):
    username = normalize_username(username)
    full_name = validate_full_name(full_name)
    encoded = hash_password(password)
    try:
        with conn.transaction():
            row = conn.execute("INSERT INTO geoattend.profiles(username,full_name,password_hash,role) VALUES(%s,%s,%s,'USER') RETURNING *",(username,full_name,encoded)).fetchone()
            return Account.from_row(row)
    except UniqueViolation:
        raise ApiError(409,'USERNAME_EXISTS','Tên tài khoản đã được sử dụng.')


def list_users(conn):
    return [Account.from_row(row) for row in conn.execute("SELECT id,username,full_name,role,is_active FROM geoattend.profiles WHERE role='USER' ORDER BY full_name,username")]


def reset_user_password(conn, account_id, new_password, now):
    encoded = hash_password(new_password)
    with conn.transaction():
        row = get_account_by_id(conn,account_id,for_update=True)
        if not row:
            raise ApiError(404,'USER_NOT_FOUND','Không tìm thấy User.')
        if row['role'] != 'USER':
            raise ApiError(403,'FORBIDDEN','Chỉ được đặt lại mật khẩu User.')
        conn.execute('UPDATE geoattend.profiles SET password_hash=%s WHERE id=%s',(encoded,account_id))
        revoke_all(conn,account_id,now)


def change_password(conn, account_id, current_password, new_password, now):
    encoded = hash_password(new_password)
    with conn.transaction():
        row = get_account_by_id(conn,account_id,for_update=True)
        if not row or not row['is_active'] or not verify_password(row['password_hash'],current_password):
            raise ApiError(401,'INVALID_PASSWORD','Mật khẩu hiện tại không đúng.')
        conn.execute('UPDATE geoattend.profiles SET password_hash=%s WHERE id=%s',(encoded,account_id))
        revoke_all(conn,account_id,now)
