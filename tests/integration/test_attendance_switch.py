from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event, Barrier
from uuid import uuid4
import hashlib
import json
import psycopg
from psycopg.rows import dict_row
import pytest
from tests.integration.test_attendance import employee, action
from tests.integration.test_office_attendance import configured, office_action
from tests.integration.test_attendance_leave import GPS

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('mode', ['OFFICE','REMOTE'])
def test_switch_closes_and_opens_atomically(configured, migrated_db, monkeypatch, mode):
    client, headers, _ = configured
    first = action(client,headers) if mode=='OFFICE' else office_action(client,headers)
    assert first.status_code == 200
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,4,tzinfo=timezone.utc))
    kind = 'SWITCH_'+mode
    assert kind in client.get('/api/attendance/status').json()['allowed_actions']
    key = str(uuid4())
    kwargs = GPS if mode == 'OFFICE' else {}
    reason = None if mode == 'OFFICE' else 'Đổi nơi làm việc'
    response = action(client,headers,1,kind,reason,key,**kwargs)
    assert response.status_code == 200
    assert response.json()['status'] == 'WORKING_'+mode and response.json()['revision'] == 2
    assert response.json()['session_id'] != first.json()['session_id'] and len(response.json()['event_ids']) == 2
    assert action(client,headers,1,kind,reason,key,**kwargs).json() == response.json()
    changed = {**kwargs,'accuracy_m':11} if mode=='OFFICE' else {}
    assert action(client,headers,1,kind,reason if mode=='OFFICE' else 'Khác',key,**changed).status_code == 409
    assert action(client,headers,2,kind,reason,**kwargs).status_code == 409
    rows = migrated_db.execute('SELECT * FROM geoattend.work_sessions ORDER BY start_time').fetchall()
    assert len(rows) == 2 and rows[0]['end_time'] == rows[1]['start_time'] == datetime(2026,10,14,4,tzinfo=timezone.utc)
    assert rows[0]['end_source'] == 'USER' and rows[1]['end_time'] is None
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.office_locations').fetchone()['n'] == 1


def test_switch_validation_preserves_source(configured, migrated_db):
    client, headers, _ = configured
    assert action(client,headers).status_code == 200
    assert action(client,headers,1,'SWITCH_OFFICE',None,**{**GPS,'latitude':12}).status_code == 403
    assert action(client,headers,1,'SWITCH_OFFICE',None).status_code == 422
    assert office_action(client,headers,1).status_code == 409
    assert client.get('/api/attendance/status').json()['status'] == 'WORKING_REMOTE'
    assert migrated_db.execute('SELECT end_time FROM geoattend.work_sessions').fetchone()['end_time'] is None
    assert action(client,headers,1,'SWITCH_OFFICE',None,**GPS).status_code == 200
    assert action(client,headers,2,'SWITCH_REMOTE',None).status_code == 422
    assert action(client,headers,2,'SWITCH_REMOTE','  ').status_code == 422
    assert client.get('/api/attendance/status').json()['status'] == 'WORKING_OFFICE'


@pytest.mark.parametrize('table', ['attendance_events','office_locations','attendance_requests'])
def test_switch_write_failure_restores_source(configured, migrated_db, table):
    client, headers, _ = configured
    first = action(client,headers)
    assert first.status_code == 200
    from psycopg import sql
    migrated_db.execute("CREATE FUNCTION geoattend.fail_switch() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test failure' USING ERRCODE='08006'; END $$")
    migrated_db.execute(sql.SQL('CREATE TRIGGER fail_switch BEFORE INSERT ON geoattend.{} FOR EACH ROW EXECUTE FUNCTION geoattend.fail_switch()').format(sql.Identifier(table)))
    migrated_db.commit()
    assert action(client,headers,1,'SWITCH_OFFICE',None,**GPS).status_code == 503
    state = client.get('/api/attendance/status').json()
    assert state['revision'] == 1 and state['open_session']['id'] == first.json()['session_id']
    for name in ('work_sessions','attendance_events','attendance_requests'):
        assert migrated_db.execute(sql.SQL('SELECT count(*) AS n FROM geoattend.{}').format(sql.Identifier(name))).fetchone()['n'] == 1
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.office_locations').fetchone()['n'] == 0


@pytest.mark.parametrize('change', ['cutoff','midnight','logout'])
def test_switch_waiting_office_does_not_close_source_early(configured, migrated_db, test_dsn, monkeypatch, change):
    from app.gis import service
    client, headers, uid = configured
    assert action(client,headers).status_code == 200
    reached = Event(); original = service.verify_office
    def marked(*args):
        reached.set(); return original(*args)
    monkeypatch.setattr(service,'verify_office',marked)
    with psycopg.connect(test_dsn) as blocker:
        blocker.execute('SELECT id FROM geoattend.office FOR UPDATE')
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(action,client,headers,1,'SWITCH_OFFICE',None,None,**GPS)
            assert reached.wait(10)
            if change == 'logout':
                blocker.execute('UPDATE geoattend.auth_sessions SET revoked_at=now() WHERE user_id=%s',(uid,))
            else:
                monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13 if change=='cutoff' else 17,tzinfo=timezone.utc))
            blocker.commit()
            response = future.result(15)
    assert response.status_code == (401 if change=='logout' else 409)
    row = migrated_db.execute('SELECT * FROM geoattend.work_sessions').fetchone()
    assert row['work_mode'] == 'REMOTE'
    if change == 'logout':
        assert row['end_time'] is None
    else:
        assert row['end_source'] == 'SYSTEM' and row['end_time'] == datetime(2026,10,14,13,tzinfo=timezone.utc)
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n'] == 1


@pytest.mark.parametrize('other', ['same_uuid','other_uuid','checkout','worker'])
def test_switch_races_keep_one_open_session(configured, migrated_db, test_dsn, monkeypatch, other):
    from app.attendance.service import act, maintain
    from app.attendance.schemas import ActionInput
    from app.errors import ApiError
    client, headers, uid = configured
    assert action(client,headers).status_code == 200
    key = uuid4(); gate = Barrier(2)
    if other == 'worker':
        monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13,tzinfo=timezone.utc))
    def attempt(second):
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            gate.wait(10)
            if second and other == 'worker':
                return maintain(conn)
            data = dict(action='SWITCH_OFFICE',**GPS)
            if second and other == 'checkout':
                data = dict(action='CHECK_OUT')
            try:
                return act(conn,uid,ActionInput(request_id=uuid4() if second and other!='same_uuid' else key,expected_revision=1,expected_work_date='2026-10-14',**data))
            except ApiError as error:
                return error.code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(attempt,second) for second in (False,True)]
        results = [f.result(15) for f in futures]
    if other == 'same_uuid':
        assert results[0] == results[1]
    elif other != 'worker':
        assert sum(r == 'STALE_REVISION' for r in results) == 1
    else:
        assert 'DAY_CLOSED' in results
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions WHERE end_time IS NULL').fetchone()['n'] == (0 if other=='worker' or any(isinstance(r,dict) and r['status']=='CHECKED_OUT' for r in results) else 1)
    assert migrated_db.execute("SELECT count(*) AS n FROM geoattend.attendance_events WHERE event_type='WORK_END'").fetchone()['n'] == 1


@pytest.mark.parametrize('mode', ['REMOTE','OFFICE'])
def test_old_payload_hash_and_replay_after_cutoff(configured, migrated_db, monkeypatch, mode):
    client, headers, _ = configured
    key = str(uuid4())
    data = dict(expected_revision=0,expected_work_date='2026-10-14',action='START_'+mode,reason='Làm việc tại nhà' if mode=='REMOTE' else None)
    if mode == 'OFFICE': data.update(latitude=10.5,longitude=106.5,accuracy_m=10.0)
    first = action(client,headers,0,'START_'+mode,data['reason'],key,**(GPS if mode=='OFFICE' else {}))
    assert first.status_code == 200
    digest = hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    assert migrated_db.execute('SELECT payload_hash FROM geoattend.attendance_requests').fetchone()['payload_hash'] == digest
    migrated_db.commit()
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,15,2,tzinfo=timezone.utc))
    assert action(client,headers,0,'START_'+mode,data['reason'],key,**(GPS if mode=='OFFICE' else {})).json() == first.json()
