import hashlib
from psycopg import sql


def apply_migrations(conn, directory):
    applied = []
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(174820001)')
        conn.execute('CREATE SCHEMA IF NOT EXISTS geoattend')
        conn.execute('REVOKE ALL ON SCHEMA geoattend FROM PUBLIC')
        ext = conn.execute("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON e.extnamespace=n.oid WHERE e.extname='postgis'").fetchone()
        if ext is None:
            conn.execute('CREATE EXTENSION postgis WITH SCHEMA public')
            extension_schema = 'public'
        else:
            extension_schema = ext['nspname']
        conn.execute(sql.SQL('SET LOCAL search_path TO geoattend, {}, public').format(sql.Identifier(extension_schema)))
        conn.execute('CREATE TABLE IF NOT EXISTS geoattend.schema_migrations(name text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())')
        for path in sorted(directory.glob('*.sql')):
            content = path.read_bytes()
            checksum = hashlib.sha256(content).hexdigest()
            old = conn.execute('SELECT checksum FROM geoattend.schema_migrations WHERE name=%s', (path.name,)).fetchone()
            if old:
                if old['checksum'] != checksum:
                    raise ValueError('Migration checksum changed: ' + path.name)
                continue
            conn.execute(content.decode('utf-8-sig'))
            conn.execute('INSERT INTO geoattend.schema_migrations(name,checksum) VALUES(%s,%s)', (path.name,checksum))
            applied.append(path.name)
    return applied


def grant_runtime(conn, role):
    identifier = sql.Identifier(role)
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA geoattend TO {}').format(identifier))
    # Reporting eligibility reads only the migration name and activation time.
    conn.execute(sql.SQL('GRANT SELECT (name, applied_at) ON geoattend.schema_migrations TO {}').format(identifier))
    tables = ('profiles','auth_sessions','auth_attempts','office','attendance_days','work_sessions','attendance_events','office_locations','attendance_requests','weekly_reports','user_avatars')
    for table in tables:
        conn.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE ON geoattend.{} TO {}').format(sql.Identifier(table), identifier))
    conn.execute(sql.SQL('GRANT DELETE ON geoattend.auth_sessions, geoattend.auth_attempts TO {}').format(identifier))
    conn.execute(sql.SQL('GRANT DELETE ON geoattend.work_sessions, geoattend.attendance_events, geoattend.office_locations TO {}').format(identifier))
    ext = conn.execute("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON e.extnamespace=n.oid WHERE e.extname='postgis'").fetchone()
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(ext['nspname']), identifier))
