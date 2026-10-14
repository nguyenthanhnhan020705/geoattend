from datetime import timedelta


def prune_auth_data(conn, now):
    attempts = conn.execute('DELETE FROM geoattend.auth_attempts WHERE attempted_at<=%s',(now-timedelta(minutes=5),)).rowcount
    sessions = conn.execute('DELETE FROM geoattend.auth_sessions WHERE revoked_at IS NOT NULL OR expires_at<=%s',(now,)).rowcount
    return attempts, sessions


def revoke_session(conn, session_id, now):
    conn.execute('UPDATE geoattend.auth_sessions SET revoked_at=%s WHERE id=%s AND revoked_at IS NULL',(now,session_id))


def revoke_all(conn, account_id, now):
    conn.execute('UPDATE geoattend.auth_sessions SET revoked_at=%s WHERE user_id=%s AND revoked_at IS NULL',(now,account_id))
