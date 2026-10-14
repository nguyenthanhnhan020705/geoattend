import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from app.accounts.repository import get_account_by_username
from app.auth.models import Account, AuthContext
from app.auth.passwords import normalize_username, hasher, verify_password
from app.auth.repository import prune_auth_data
from app.errors import ApiError

SESSION_TTL_SECONDS = 43200
DUMMY_HASH = hasher.hash('dummy-verification-only')


@dataclass(frozen=True)
class LoginResult:
    account: Account
    raw_token: str
    csrf_token: str
    expires_at: datetime


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def login(conn, username, password, now):
    username = normalize_username(username)
    error = None
    result = None
    with conn.transaction():
        lock = int.from_bytes(hashlib.sha256(('login:'+username).encode()).digest()[:8], 'big', signed=True)
        conn.execute('SELECT pg_advisory_xact_lock(%s)',(lock,))
        prune_auth_data(conn,now)
        n = conn.execute('SELECT count(*) AS n FROM geoattend.auth_attempts WHERE username=%s AND attempted_at>%s',(username,now-timedelta(minutes=5))).fetchone()['n']
        if n >= 5:
            error = ApiError(429,'TOO_MANY_ATTEMPTS','Đã thử sai nhiều lần. Vui lòng thử lại sau 5 phút.')
        else:
            row = get_account_by_username(conn,username,for_update=True)
            valid = verify_password(row['password_hash'] if row else DUMMY_HASH,password)
            if not row or not row['is_active'] or not valid:
                conn.execute('INSERT INTO geoattend.auth_attempts(username,attempted_at) VALUES(%s,%s)',(username,now))
                error = ApiError(401,'INVALID_CREDENTIALS','Tên tài khoản hoặc mật khẩu không đúng.')
            else:
                raw = secrets.token_urlsafe(32)
                csrf = secrets.token_urlsafe(32)
                expiry = now+timedelta(seconds=SESSION_TTL_SECONDS)
                conn.execute('INSERT INTO geoattend.auth_sessions(user_id,token_hash,csrf_token,expires_at,created_at) VALUES(%s,%s,%s,%s,%s)',(row['id'],token_hash(raw),csrf,expiry,now))
                result = LoginResult(Account.from_row(row),raw,csrf,expiry)
    # Failed attempts must commit before returning the authentication error.
    if error:
        raise error
    return result


def resolve_session(conn, raw_token, now):
    if not raw_token or len(raw_token)>256:
        raise ApiError(401,'AUTH_REQUIRED','Vui lòng đăng nhập.')
    row = conn.execute('SELECT p.*,s.id AS session_id,s.csrf_token FROM geoattend.auth_sessions s JOIN geoattend.profiles p ON p.id=s.user_id WHERE s.token_hash=%s AND s.revoked_at IS NULL AND s.expires_at>%s AND p.is_active', (token_hash(raw_token),now)).fetchone()
    if not row:
        raise ApiError(401,'AUTH_REQUIRED','Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.')
    return AuthContext(Account.from_row(row),row['session_id'],row['csrf_token'])
