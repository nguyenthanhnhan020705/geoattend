import json
from psycopg import sql
from app import clock
from app.errors import ApiError
from app.attendance.service import validate_session


def extension_schema(conn):
    row=conn.execute("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON e.extnamespace=n.oid WHERE e.extname='postgis'").fetchone()
    if row is None:
        raise ApiError(503,'GIS_UNAVAILABLE','Dịch vụ xác minh vị trí chưa sẵn sàng.')
    return sql.Identifier(row['nspname'])


def get_office(conn):
    ext=extension_schema(conn)
    row=conn.execute(sql.SQL('SELECT id,name,address,{}.ST_AsGeoJSON(geom)::json AS geom,revision,updated_at FROM geoattend.office').format(ext)).fetchone()
    return row or dict(id=None,name='',address='',geom=None,revision=0,updated_at=None)


def save_office(conn,body,context):
    with conn.transaction():
        profile=conn.execute('SELECT role,is_active FROM geoattend.profiles WHERE id=%s FOR UPDATE',(context.account.id,)).fetchone()
        if not profile or not profile['is_active'] or profile['role']!='ADMIN':
            raise ApiError(403,'FORBIDDEN','Chức năng dành cho Admin.')
        validate_session(conn,context.account.id,context.session_id,clock.utc_now())
        conn.execute('SELECT pg_advisory_xact_lock(174820003)')
        old=conn.execute('SELECT id,revision FROM geoattend.office FOR UPDATE').fetchone()
        validate_session(conn,context.account.id,context.session_id,clock.utc_now())
        if body.expected_revision!=(old['revision'] if old else 0):
            raise ApiError(409,'STALE_REVISION','Vùng văn phòng đã thay đổi. Tải lại để xem phiên bản mới trước khi lưu.')
        ext=extension_schema(conn)
        geometry=json.dumps(body.geom.model_dump(),allow_nan=False)
        valid=conn.execute(sql.SQL('WITH shape AS (SELECT {s}.ST_SetSRID({s}.ST_GeomFromGeoJSON(%s),4326) AS g) SELECT {s}.ST_IsValid(g) AND NOT {s}.ST_IsEmpty(g) AND {s}.ST_Area(g)>0 AS valid FROM shape').format(s=ext),(geometry,)).fetchone()['valid']
        if not valid:
            raise ApiError(422,'INVALID_POLYGON','Vùng văn phòng phải có diện tích và không tự cắt hoặc chồng lấn.')
        if old:
            conn.execute(sql.SQL('UPDATE geoattend.office SET name=%s,address=%s,geom={s}.ST_SetSRID({s}.ST_GeomFromGeoJSON(%s),4326),revision=revision+1,updated_at=%s WHERE id=%s').format(s=ext),(body.name,body.address,geometry,clock.utc_now(),old['id']))
        else:
            conn.execute(sql.SQL('INSERT INTO geoattend.office(name,address,geom,revision,updated_at) VALUES(%s,%s,{s}.ST_SetSRID({s}.ST_GeomFromGeoJSON(%s),4326),1,%s)').format(s=ext),(body.name,body.address,geometry,clock.utc_now()))
        return get_office(conn)


def verify_office(conn,latitude,longitude):
    # Keep the shared lock until the attendance transaction completes, so
    # saved office_revision is exactly the polygon used for verification.
    office=conn.execute('SELECT id,revision,geom IS NOT NULL AS configured FROM geoattend.office FOR SHARE').fetchone()
    if not office or not office['configured']:
        raise ApiError(409,'OFFICE_NOT_CONFIGURED','Admin chưa cấu hình vùng văn phòng. Bạn có thể chọn Remote và nhập lý do.')
    ext=extension_schema(conn)
    inside=conn.execute(sql.SQL('SELECT {s}.ST_Covers(geom,{s}.ST_SetSRID({s}.ST_MakePoint(%s,%s),4326)) AS inside FROM geoattend.office WHERE id=%s').format(s=ext),(longitude,latitude,office['id'])).fetchone()['inside']
    if not inside:
        raise ApiError(403,'OUTSIDE_GEOFENCE','Vị trí nằm ngoài vùng văn phòng. Hãy kiểm tra GPS hoặc tự chọn Remote.')
    return office
