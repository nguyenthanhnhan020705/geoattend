def get_account_by_username(conn, username, for_update=False):
    suffix = ' FOR UPDATE' if for_update else ''
    return conn.execute('SELECT * FROM geoattend.profiles WHERE username=%s'+suffix,(username,)).fetchone()


def get_account_by_id(conn, account_id, for_update=False):
    suffix = ' FOR UPDATE' if for_update else ''
    return conn.execute('SELECT * FROM geoattend.profiles WHERE id=%s'+suffix,(account_id,)).fetchone()
