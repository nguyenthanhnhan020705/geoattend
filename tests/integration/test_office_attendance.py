from datetime import datetime,timezone
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import hashlib,json
import psycopg
from psycopg.rows import dict_row
import pytest
from tests.integration.test_attendance import employee,action
from tests.integration.test_office import POLYGON

pytestmark=pytest.mark.integration


@pytest.fixture
def configured(employee,migrated_db):
    migrated_db.execute('INSERT INTO geoattend.office(name,address,geom,revision) VALUES(%s,%s,ST_GeomFromGeoJSON(%s),1)',('Office','HCM',json.dumps(POLYGON)))
    migrated_db.commit()
    return employee


def office_action(client,headers,revision=0,latitude=10.5,longitude=106.5,accuracy_m=15,request_id=None):
    return action(client,headers,revision,'START_OFFICE',None,request_id,latitude=latitude,longitude=longitude,accuracy_m=accuracy_m)


@pytest.mark.parametrize('lat,lon,accuracy',[(10.5,106.5,10),(10,106,50000),(10.5,106,0)])
def test_office_inside_boundary_large_accuracy(configured,migrated_db,lat,lon,accuracy):
    client,headers,_=configured
    response=office_action(client,headers,latitude=lat,longitude=lon,accuracy_m=accuracy)
    assert response.status_code==200 and response.json()['status']=='WORKING_OFFICE'
    row=migrated_db.execute('SELECT s.work_mode,s.office_revision,e.location_verified,l.accuracy_m,ST_X(l.point) AS lon,ST_Y(l.point) AS lat,l.expires_at-l.recorded_at AS ttl FROM geoattend.work_sessions s JOIN geoattend.attendance_events e ON e.session_id=s.id JOIN geoattend.office_locations l ON l.session_id=s.id').fetchone()
    assert row['office_revision']==1 and row['location_verified'] is True
    assert (row['lon'],row['lat'],row['accuracy_m'])==(lon,lat,accuracy)
    assert row['ttl'].total_seconds()==30*86400
    assert 'latitude' not in response.text and 'longitude' not in response.text


def test_outside_and_unconfigured_preserve_state(employee,migrated_db):
    client,headers,_=employee
    assert office_action(client,headers).status_code==409
    assert client.get('/api/attendance/status').json()['status']=='NOT_STARTED'
    migrated_db.execute('INSERT INTO geoattend.office(name,address,geom,revision) VALUES(%s,%s,ST_GeomFromGeoJSON(%s),1)',('Office','HCM',json.dumps(POLYGON))); migrated_db.commit()
    assert office_action(client,headers,latitude=12).status_code==403
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==0
    assert client.get('/api/attendance/status').json()['status']=='NOT_STARTED'


@pytest.mark.parametrize('key,value',[('latitude',91),('longitude',181),('accuracy_m',-1),('latitude',None),('accuracy_m','NaN'),('longitude',True)])
def test_invalid_gps_rejected(configured,key,value):
    client,headers,_=configured
    data=dict(latitude=10.5,longitude=106.5,accuracy_m=5);data[key]=value
    assert action(client,headers,kind='START_OFFICE',reason=None,**data).status_code==422


def test_office_replay_checkout_and_new_verification(configured,migrated_db):
    client,headers,_=configured
    key=str(uuid4()); first=office_action(client,headers,request_id=key)
    assert first.status_code==200
    assert office_action(client,headers,request_id=key).json()==first.json()
    assert office_action(client,headers,latitude=10.6,request_id=key).status_code==409
    assert action(client,headers,1,'CHECK_OUT',None).status_code==200
    moved={'type':'Polygon','coordinates':[[[108,10],[109,10],[109,11],[108,11],[108,10]]]}
    migrated_db.execute('UPDATE geoattend.office SET geom=ST_GeomFromGeoJSON(%s),revision=2',(json.dumps(moved),)); migrated_db.commit()
    assert office_action(client,headers,2).status_code==403
    second=office_action(client,headers,2,longitude=108.5)
    assert second.status_code==200
    assert [r['office_revision'] for r in migrated_db.execute('SELECT office_revision FROM geoattend.work_sessions ORDER BY office_revision')]==[1,2]


def test_gps_insert_failure_rolls_back_everything(configured,migrated_db):
    client,headers,_=configured
    migrated_db.execute("CREATE FUNCTION geoattend.fail_gps() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test failure' USING ERRCODE='08006'; END $$")
    migrated_db.execute('CREATE TRIGGER fail_gps BEFORE INSERT ON geoattend.office_locations FOR EACH ROW EXECUTE FUNCTION geoattend.fail_gps()'); migrated_db.commit()
    assert office_action(client,headers).status_code==503
    for table in ('attendance_days','work_sessions','attendance_events','office_locations','attendance_requests'):
        from psycopg import sql
        assert migrated_db.execute(sql.SQL('SELECT count(*) AS n FROM geoattend.{}').format(sql.Identifier(table))).fetchone()['n']==0


def test_phase2_remote_hash_remains_replayable(configured,migrated_db):
    client,headers,_=configured
    key=str(uuid4()); first=action(client,headers,request_id=key)
    assert first.status_code==200
    original=dict(expected_revision=0,expected_work_date='2026-10-14',action='START_REMOTE',reason='Làm việc tại nhà')
    old_hash=hashlib.sha256(json.dumps(original,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    row=migrated_db.execute('SELECT payload_hash FROM geoattend.attendance_requests').fetchone()
    assert row['payload_hash']==old_hash
    assert action(client,headers,request_id=key).json()==first.json()


def test_office_row_wait_crossing_cutoff_rejects(configured,test_dsn,migrated_db,monkeypatch):
    from app.gis import service
    client,headers,_=configured
    reached=Event();original=service.verify_office
    def marked(*args): reached.set();return original(*args)
    monkeypatch.setattr(service,'verify_office',marked)
    with psycopg.connect(test_dsn,row_factory=dict_row) as blocker:
        blocker.execute('SELECT id FROM geoattend.office FOR UPDATE')
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending=executor.submit(office_action,client,headers)
            assert reached.wait(10)
            monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13,tzinfo=timezone.utc))
            blocker.commit()
            response=pending.result(15)
    assert response.status_code==409 and response.json()['code']=='DAY_CLOSED'
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==0


@pytest.mark.parametrize('change',['polygon','logout'])
def test_waiting_office_uses_current_polygon_and_session(configured,test_dsn,migrated_db,monkeypatch,change):
    from app.gis import service
    client,headers,uid=configured
    reached=Event();original=service.verify_office
    def marked(*args):reached.set();return original(*args)
    monkeypatch.setattr(service,'verify_office',marked)
    with psycopg.connect(test_dsn) as blocker:
        blocker.execute('SELECT id FROM geoattend.office FOR UPDATE')
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(office_action,client,headers)
            assert reached.wait(10)
            if change=='polygon':
                moved={'type':'Polygon','coordinates':[[[108,10],[109,10],[109,11],[108,11],[108,10]]]}
                blocker.execute('UPDATE geoattend.office SET geom=ST_GeomFromGeoJSON(%s),revision=revision+1',(json.dumps(moved),))
            else:
                blocker.execute('UPDATE geoattend.auth_sessions SET revoked_at=now() WHERE user_id=%s',(uid,))
            blocker.commit()
            response=future.result(15)
    assert response.status_code==(403 if change=='polygon' else 401)
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==0
