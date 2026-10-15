from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Barrier
from uuid import uuid4
import psycopg
from psycopg.rows import dict_row
import pytest
from tests.integration.test_attendance import employee, action
from tests.integration.test_office_attendance import configured

pytestmark = pytest.mark.integration
GPS = dict(latitude=10.5,longitude=106.5,accuracy_m=10)


@pytest.mark.parametrize('leave', ['MORNING_LEAVE','FULL_DAY_LEAVE'])
def test_leave_reason_input_history_and_cutoff(employee, migrated_db, monkeypatch, leave):
    client, headers, _ = employee
    for reason in (None,'','  ','x'*1001):
        assert action(client,headers,0,leave,reason).status_code == 422
    assert action(client,headers,0,leave,'Nghỉ',latitude=None).status_code == 422
    assert action(client,headers,0,leave,'Nghỉ',unexpected=True).status_code == 422
    saved = action(client,headers,0,leave,'  Có việc riêng  ')
    assert saved.status_code == 200 and saved.json()['status'] == leave
    assert saved.json()['session_id'] is None and len(saved.json()['event_ids']) == 1
    assert action(client,headers,1,leave,'Nghỉ nữa').status_code == 409
    history = client.get('/api/attendance/history').json()['items'][0]
    assert history['sessions'] == []
    assert history['events'][0]['event_type'] == leave
    assert history['events'][0]['reason'] == 'Có việc riêng'
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13,tzinfo=timezone.utc))
    assert client.get('/api/attendance/status').json()['status'] == leave
    assert client.get('/api/attendance/status').json()['allowed_actions'] == []
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.office_locations').fetchone()['n'] == 0


@pytest.mark.parametrize('leave', ['MORNING_LEAVE','FULL_DAY_LEAVE'])
@pytest.mark.parametrize('mode', ['REMOTE','OFFICE'])
def test_leave_then_start_and_cancel_atomic(configured, migrated_db, leave, mode):
    client, headers, _ = configured
    assert action(client,headers,0,leave,'Việc gia đình').status_code == 200
    kind = ('CANCEL_LEAVE_START_' if leave == 'FULL_DAY_LEAVE' else 'START_') + mode
    state = client.get('/api/attendance/status').json()
    assert kind in state['allowed_actions']
    assert action(client,headers,1,kind,None).status_code == 422
    if mode == 'OFFICE':
        assert action(client,headers,1,kind,None,**{**GPS,'latitude':12}).status_code == 403
        assert client.get('/api/attendance/status').json()['status'] == leave
    key = str(uuid4())
    response = action(client,headers,1,kind,'  Quay lại  ' if mode == 'REMOTE' else None,key,**(GPS if mode=='OFFICE' else {}))
    assert response.status_code == 200 and response.json()['status'] == 'WORKING_'+mode
    assert response.json()['revision'] == 2
    assert action(client,headers,1,kind,'Quay lại' if mode=='REMOTE' else None,key,**(GPS if mode=='OFFICE' else {})).json() == response.json()
    history = client.get('/api/attendance/history').json()['items'][0]
    assert history['status'] == 'WORKING_'+mode and len(history['sessions']) == 1
    kinds = [e['event_type'] for e in history['events']]
    assert kinds.count(leave) == 1 and kinds.count('WORK_START') == 1
    assert kinds.count('LEAVE_CANCELLED') == (leave == 'FULL_DAY_LEAVE')
    assert len(response.json()['event_ids']) == (2 if leave == 'FULL_DAY_LEAVE' else 1)


@pytest.mark.parametrize('kind', ['MORNING_LEAVE','FULL_DAY_LEAVE','CANCEL_LEAVE_START_REMOTE','CANCEL_LEAVE_START_OFFICE'])
def test_leave_invalid_from_working(configured, kind):
    client, headers, _ = configured
    assert action(client,headers).status_code == 200
    response = action(client,headers,1,kind,None if kind.endswith('OFFICE') else 'Lý do',**(GPS if kind.endswith('OFFICE') else {}))
    assert response.status_code == 409
    assert client.get('/api/attendance/status').json()['status'] == 'WORKING_REMOTE'


@pytest.mark.parametrize('failed_event', ['LEAVE_CANCELLED','WORK_START'])
def test_cancel_insert_failure_retains_full_leave(configured, migrated_db, failed_event):
    client, headers, _ = configured
    assert action(client,headers,0,'FULL_DAY_LEAVE','Nghỉ').status_code == 200
    migrated_db.execute("CREATE FUNCTION geoattend.fail_cancel() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.event_type='"+failed_event+"' THEN RAISE EXCEPTION 'test failure' USING ERRCODE='08006'; END IF; RETURN NEW; END $$")
    migrated_db.execute('CREATE TRIGGER fail_cancel BEFORE INSERT ON geoattend.attendance_events FOR EACH ROW EXECUTE FUNCTION geoattend.fail_cancel()')
    migrated_db.commit()
    assert action(client,headers,1,'CANCEL_LEAVE_START_OFFICE',None,**GPS).status_code == 503
    assert client.get('/api/attendance/status').json()['status'] == 'FULL_DAY_LEAVE'
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n'] == 0
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_events').fetchone()['n'] == 1
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_requests').fetchone()['n'] == 1


@pytest.mark.parametrize('change', ['cutoff','midnight','logout','reset','inactive'])
def test_cancel_waiting_profile_rechecks_context(employee, test_dsn, migrated_db, monkeypatch, change):
    from app.attendance import service
    client, headers, uid = employee
    assert action(client,headers,0,'FULL_DAY_LEAVE','Nghỉ').status_code == 200
    reached = Event(); original = service.lock_user
    def marked(conn,user_id):
        reached.set(); return original(conn,user_id)
    monkeypatch.setattr(service,'lock_user',marked)
    with psycopg.connect(test_dsn,row_factory=dict_row) as blocker:
        blocker.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE',(uid,))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(action,client,headers,1,'CANCEL_LEAVE_START_REMOTE','Quay lại')
            assert reached.wait(10)
            if change in ('cutoff','midnight'):
                monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13 if change=='cutoff' else 17,tzinfo=timezone.utc))
            elif change == 'inactive':
                blocker.execute('UPDATE geoattend.profiles SET is_active=false WHERE id=%s',(uid,))
            elif change == 'reset':
                from app.accounts.service import reset_user_password
                reset_user_password(blocker,uid,'Reset12345',datetime(2026,10,14,2,tzinfo=timezone.utc))
            else:
                blocker.execute('UPDATE geoattend.auth_sessions SET revoked_at=now() WHERE user_id=%s',(uid,))
            blocker.commit()
            response = future.result(15)
    assert response.status_code == (409 if change in ('cutoff','midnight') else 401)
    assert migrated_db.execute('SELECT status FROM geoattend.attendance_days').fetchone()['status'] == 'FULL_DAY_LEAVE'
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n'] == 0


def test_two_leave_requests_same_revision(employee, test_dsn, migrated_db):
    from app.attendance.service import act
    from app.attendance.schemas import ActionInput
    from app.errors import ApiError
    from psycopg.rows import dict_row
    _, _, uid = employee
    gate = Barrier(2)
    def attempt(kind):
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            gate.wait(10)
            try:
                return act(conn,uid,ActionInput(request_id=uuid4(),expected_revision=0,expected_work_date='2026-10-14',action=kind,reason='Nghỉ'))
            except ApiError as error:
                return error.code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(attempt,k) for k in ('MORNING_LEAVE','FULL_DAY_LEAVE')]
        results = [f.result(15) for f in futures]
    assert sum(r == 'STALE_REVISION' for r in results) == 1
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_events').fetchone()['n'] == 1
