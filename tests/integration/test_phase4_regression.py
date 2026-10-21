from datetime import datetime, timezone
from uuid import uuid4
import pytest
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.conninfo import make_conninfo
from tests.integration.test_attendance import employee, action
from tests.integration.test_office_attendance import configured, office_action
from tests.integration.test_attendance_leave import GPS

pytestmark = pytest.mark.integration

# Literal approved transition table; invalid actions must leave the day unchanged.
ALLOWED = {
    'NOT_STARTED': ['START_OFFICE','START_REMOTE','MORNING_LEAVE','FULL_DAY_LEAVE'],
    'WORKING_OFFICE': ['CHECK_OUT','START_LUNCH','SWITCH_REMOTE'],
    'WORKING_REMOTE': ['CHECK_OUT','START_LUNCH','SWITCH_OFFICE'],
    'LUNCH_BREAK': ['START_OFFICE','START_REMOTE'],
    'MORNING_LEAVE': ['START_OFFICE','START_REMOTE'],
    'FULL_DAY_LEAVE': [],
    'CHECKED_OUT': [],
}
ACTIONS = ['START_OFFICE','START_REMOTE','MORNING_LEAVE','FULL_DAY_LEAVE','CHECK_OUT','START_LUNCH','SWITCH_OFFICE','SWITCH_REMOTE','CANCEL_LEAVE_START_OFFICE','CANCEL_LEAVE_START_REMOTE']


@pytest.mark.parametrize('state', list(ALLOWED))
def test_all_forbidden_transitions_preserve_state(configured, migrated_db, state):
    client, headers, _ = configured
    if state == 'WORKING_OFFICE':
        assert office_action(client,headers).status_code == 200
    elif state in ('WORKING_REMOTE','LUNCH_BREAK','CHECKED_OUT'):
        assert action(client,headers).status_code == 200
        if state != 'WORKING_REMOTE':
            assert action(client,headers,1,'START_LUNCH' if state=='LUNCH_BREAK' else 'CHECK_OUT','Personal appointment').status_code == 200
    elif state in ('MORNING_LEAVE','FULL_DAY_LEAVE'):
        assert action(client,headers,0,state,'Nghỉ').status_code == 200
    before = client.get('/api/attendance/status').json()
    assert set(before['allowed_actions']) == set(ALLOWED[state])
    for kind in ACTIONS:
        if kind in ALLOWED[state]: continue
        is_office = kind.endswith('OFFICE')
        reason = None if is_office or kind in ('CHECK_OUT','START_LUNCH') else 'Lý do'
        response = action(client,headers,before['revision'],kind,reason,**(GPS if is_office else {}))
        assert response.status_code == 409, (state,kind,response.text)
    after = client.get('/api/attendance/status').json()
    assert (after['status'],after['revision'],after['open_session']) == (before['status'],before['revision'],before['open_session'])


@pytest.mark.parametrize('hour,minute,allowed', [(12,59,True),(13,0,False),(13,1,False)])
@pytest.mark.parametrize('kind', ['START_REMOTE','CANCEL_LEAVE_START_REMOTE','SWITCH_REMOTE'])
def test_phase4_start_cutoff_boundaries(configured, migrated_db, monkeypatch, hour, minute, allowed, kind):
    client, headers, _ = configured
    if kind == 'START_REMOTE':
        action(client,headers)
        assert action(client,headers,1,'START_LUNCH',None).status_code == 200
        revision = 2
    elif kind == 'CANCEL_LEAVE_START_REMOTE':
        assert action(client,headers,0,'FULL_DAY_LEAVE','Nghỉ').status_code == 200
        revision = 1
    else:
        assert office_action(client,headers).status_code == 200
        revision = 1
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,hour,minute,tzinfo=timezone.utc))
    response = action(client,headers,revision,kind,'Quay lại')
    assert response.status_code == (200 if allowed and kind!='CANCEL_LEAVE_START_REMOTE' else 409)
    if allowed and kind=='CANCEL_LEAVE_START_REMOTE':
        assert response.json()['code']=='DAY_FINISHED'
    if not allowed:
        assert response.json()['code'] == 'DAY_CLOSED'
        assert migrated_db.execute("SELECT count(*) AS n FROM geoattend.attendance_events WHERE event_type='LEAVE_CANCELLED'").fetchone()['n'] == 0


def test_lunch_uuid_replays_after_cutoff_and_next_day(employee, migrated_db, monkeypatch):
    client, headers, _ = employee
    assert action(client,headers).status_code == 200
    key = str(uuid4())
    first = action(client,headers,1,'START_LUNCH',None,key)
    assert first.status_code == 200
    for moment in (datetime(2026,10,14,13,tzinfo=timezone.utc),datetime(2026,10,15,2,tzinfo=timezone.utc)):
        monkeypatch.setattr('app.clock.utc_now',lambda:moment)
        assert action(client,headers,1,'START_LUNCH',None,key).json() == first.json()
    assert migrated_db.execute("SELECT count(*) AS n FROM geoattend.attendance_events WHERE event_type='DAY_END'").fetchone()['n'] == 1


def test_runtime_role_phase4_actions_and_worker(configured, migrated_db, test_dsn, monkeypatch):
    from app.db.migrations import grant_runtime
    from app.attendance.service import act, history, maintain
    from app.attendance.schemas import ActionInput
    _, _, uid = configured
    role = 'phase4_runtime_'+uuid4().hex
    migrated_db.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    grant_runtime(migrated_db,role); migrated_db.commit()
    try:
        with psycopg.connect(make_conninfo(test_dsn,user=role),row_factory=dict_row) as conn:
            steps = [dict(action='MORNING_LEAVE',reason='Nghỉ'),dict(action='START_OFFICE',**GPS),dict(action='SWITCH_REMOTE',reason='Về nhà'),dict(action='START_LUNCH'),dict(action='START_OFFICE',**GPS)]
            for revision, data in enumerate(steps):
                answer = act(conn,uid,ActionInput(request_id=uuid4(),expected_revision=revision,expected_work_date='2026-10-14',**data))
                assert answer['revision'] == revision+1
            monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13,tzinfo=timezone.utc))
            assert maintain(conn) == 1 and maintain(conn) == 0
            day = history(conn,uid,None,None,1,20)['items'][0]
            assert day['status'] == 'CHECKED_OUT' and len(day['sessions']) == 3
            assert sum(event['event_type']=='LEAVE_CANCELLED' for event in day['events']) == 0
            assert sum(event['event_type']=='MORNING_LEAVE' for event in day['events']) == 1
    finally:
        migrated_db.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
        migrated_db.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
        migrated_db.commit()
