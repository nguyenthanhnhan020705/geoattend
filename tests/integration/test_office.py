from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest

pytestmark=pytest.mark.integration
POLYGON={'type':'Polygon','coordinates':[[[106,10],[107,10],[107,11],[106,11],[106,10]]]}


def office_body(revision=0,geom=None):
    return dict(name='Văn phòng',address='TP.HCM',geom=deepcopy(POLYGON if geom is None else geom),expected_revision=revision)


def admin_headers(client):
    from tests.test_auth_api import signin
    return {'X-CSRF-Token':signin(client).json()['csrf_token']}


def test_office_permissions_and_first_save(api_client):
    assert api_client.get('/api/admin/office').status_code==401
    headers=admin_headers(api_client)
    empty=api_client.get('/api/admin/office')
    assert empty.status_code==200 and empty.json()['revision']==0 and empty.json()['geom'] is None
    assert api_client.put('/api/admin/office',json=office_body()).status_code==403
    saved=api_client.put('/api/admin/office',headers=headers,json=office_body())
    assert saved.status_code==200 and saved.json()['revision']==1
    assert saved.json()['geom']==POLYGON
    assert api_client.get('/api/admin/office').json()['geom']==POLYGON
    assert api_client.put('/api/admin/office',headers=headers,json=office_body()).status_code==409
    created=api_client.post('/api/admin/users',headers=headers,json={'username':'worker','full_name':'Nhân viên','password':'Worker1234'})
    assert created.status_code==201
    from tests.test_auth_api import signin
    worker={'X-CSRF-Token':signin(api_client,'worker','Worker1234').json()['csrf_token']}
    assert api_client.get('/api/admin/office').status_code==403
    assert api_client.put('/api/admin/office',headers=worker,json=office_body(1)).status_code==403


@pytest.mark.parametrize('geom',[
    {'type':'Polygon','coordinates':[]},
    {'type':'Point','coordinates':[106,10]},
    {'type':'Polygon','coordinates':[[[106,10],[107,11],[107,10],[106,11],[106,10]]]},
    {'type':'Polygon','coordinates':[[[106,10],[106,10],[106,10],[106,10]]]},
    {'type':'Polygon','coordinates':[[[181,10],[182,10],[182,11],[181,10]]]},
    {'type':'Polygon','coordinates':[[[106,10],[107,10],[107,11],[106,11]]]},
    {'type':'Polygon','coordinates':[[[106,10,0],[107,10,0],[107,11,0],[106,10,0]]]},
])
def test_invalid_polygon_does_not_write(api_client,migrated_db,geom):
    headers=admin_headers(api_client)
    result=api_client.put('/api/admin/office',headers=headers,json=office_body(geom=geom))
    assert result.status_code==422
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.office').fetchone()['n']==0


def test_concurrent_initial_office_save_only_one_revision(api_client,test_dsn,migrated_db):
    import psycopg
    from psycopg.rows import dict_row
    from app.gis.schemas import OfficeInput
    from app.gis.service import save_office
    from app.auth.service import resolve_session
    from app.clock import utc_now
    from app.errors import ApiError
    admin_headers(api_client)
    context=resolve_session(migrated_db,api_client.cookies.get('geoattend_session'),utc_now())
    migrated_db.commit()
    barrier=Barrier(2)
    def save():
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            barrier.wait(10)
            try: return save_office(conn,OfficeInput(**office_body()),context)['revision']
            except ApiError as error: return error.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(save) for _ in range(2)]
        assert sorted(f.result(15) for f in futures)==[1,409]


def test_office_functions_support_extensions_schema(db):
    from pathlib import Path
    from app.gis.schemas import OfficeInput
    from app.gis.service import save_office,verify_office,get_office
    from app.db.migrations import apply_migrations
    from app.accounts.bootstrap import create_initial_admin
    from app.auth.service import login,resolve_session
    from app.clock import utc_now
    db.execute('DROP EXTENSION postgis CASCADE')
    db.execute('CREATE SCHEMA IF NOT EXISTS extensions')
    db.execute('CREATE EXTENSION postgis WITH SCHEMA extensions')
    db.commit()
    try:
        apply_migrations(db,Path('migrations'))
        create_initial_admin(db,'admin','Admin','Admin1234')
        logged=login(db,'admin','Admin1234',utc_now())
        context=resolve_session(db,logged.raw_token,utc_now())
        db.commit()
        assert save_office(db,OfficeInput(**office_body()),context)['revision']==1
        with db.transaction():
            assert verify_office(db,10.5,106.5)['revision']==1
        assert get_office(db)['geom']==POLYGON
    finally:
        db.rollback()
        db.execute('DROP SCHEMA IF EXISTS geoattend CASCADE')
        db.execute('DROP EXTENSION postgis CASCADE')
        db.execute('CREATE EXTENSION postgis WITH SCHEMA public')
        db.commit()
