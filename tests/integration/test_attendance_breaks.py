from datetime import datetime, timezone
from uuid import uuid4
import pytest
from tests.integration.test_attendance import employee, action
from tests.integration.test_office_attendance import configured, office_action

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('first_mode,next_mode', [('REMOTE','REMOTE'),('OFFICE','OFFICE'),('REMOTE','OFFICE'),('OFFICE','REMOTE')])
def test_lunch_closes_session_and_resume_creates_new(configured, migrated_db, monkeypatch, first_mode, next_mode):
    client, headers, _ = configured
    first = office_action(client, headers) if first_mode == 'OFFICE' else action(client, headers)
    assert first.status_code == 200
    monkeypatch.setattr('app.clock.utc_now', lambda: datetime(2026,10,14,5,tzinfo=timezone.utc))
    key = str(uuid4())
    lunch = action(client, headers, 1, 'START_LUNCH', None, key)
    assert lunch.status_code == 200
    assert lunch.json()['status'] == 'LUNCH_BREAK' and lunch.json()['revision'] == 2
    assert len(lunch.json()['event_ids']) == 2
    assert action(client, headers, 1, 'START_LUNCH', None, key).json() == lunch.json()
    state = client.get('/api/attendance/status').json()
    assert state['open_session'] is None
    assert set(state['allowed_actions']) == {'START_OFFICE','START_REMOTE'}
    assert action(client, headers, 2, reason=None).status_code == 422
    assert office_action(client, headers, 2, latitude=12).status_code == 403
    assert client.get('/api/attendance/status').json()['status'] == 'LUNCH_BREAK'
    monkeypatch.setattr('app.clock.utc_now', lambda: datetime(2026,10,14,6,tzinfo=timezone.utc))
    resumed = office_action(client, headers, 2) if next_mode == 'OFFICE' else action(client, headers, 2, reason='Buổi chiều')
    assert resumed.status_code == 200 and resumed.json()['session_id'] != first.json()['session_id']
    assert action(client, headers, 3, 'CHECK_OUT', None).status_code == 200
    rows = migrated_db.execute('SELECT * FROM geoattend.work_sessions ORDER BY start_time').fetchall()
    assert len(rows) == 2
    assert rows[0]['end_time'] == datetime(2026,10,14,5,tzinfo=timezone.utc)
    assert rows[1]['start_time'] == datetime(2026,10,14,6,tzinfo=timezone.utc)
    assert rows[0]['end_source'] == 'USER'
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.office_locations').fetchone()['n'] == (first_mode == 'OFFICE') + (next_mode == 'OFFICE')


def test_lunch_invalid_state_and_gps(employee):
    client, headers, _ = employee
    assert action(client, headers, 0, 'START_LUNCH', None).status_code == 409
    assert action(client, headers, 0, 'START_LUNCH', None, latitude=None).status_code == 422


@pytest.mark.parametrize('hour,minute', [(12,59),(13,0),(14,0),(23,0)])
def test_lunch_cutoff_catchup_is_idempotent(employee, migrated_db, monkeypatch, hour, minute):
    from app.attendance.service import maintain
    client, headers, _ = employee
    action(client, headers)
    lunch = action(client, headers, 1, 'START_LUNCH', None)
    assert lunch.status_code == 200
    monkeypatch.setattr('app.clock.utc_now', lambda: datetime(2026,10,14,hour,minute,tzinfo=timezone.utc))
    assert maintain(migrated_db) == (0 if hour < 13 else 1)
    assert maintain(migrated_db) == 0
    migrated_db.commit()
    ends = migrated_db.execute("SELECT * FROM geoattend.attendance_events WHERE event_type='DAY_END'").fetchall()
    assert len(ends) == (0 if hour < 13 else 1)
    if ends:
        assert ends[0]['source'] == 'SYSTEM' and ends[0]['session_id'] is None
        assert ends[0]['event_time'] == datetime(2026,10,14,13,tzinfo=timezone.utc)
        assert ends[0]['recorded_at'] == datetime(2026,10,14,hour,minute,tzinfo=timezone.utc)
    assert migrated_db.execute('SELECT end_time FROM geoattend.work_sessions').fetchone()['end_time'] == datetime(2026,10,14,2,tzinfo=timezone.utc)
    status = client.get('/api/attendance/status').json()
    assert status['status'] == ('NOT_STARTED' if hour == 23 else 'LUNCH_BREAK' if hour < 13 else 'CHECKED_OUT')


def test_lunch_event_failure_rolls_back(employee, migrated_db):
    client, headers, _ = employee
    action(client, headers)
    migrated_db.execute("CREATE FUNCTION geoattend.fail_lunch() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.event_type='LUNCH_START' THEN RAISE EXCEPTION 'test failure' USING ERRCODE='08006'; END IF; RETURN NEW; END $$")
    migrated_db.execute('CREATE TRIGGER fail_lunch BEFORE INSERT ON geoattend.attendance_events FOR EACH ROW EXECUTE FUNCTION geoattend.fail_lunch()')
    migrated_db.commit()
    assert action(client, headers, 1, 'START_LUNCH', None).status_code == 503
    assert client.get('/api/attendance/status').json()['status'] == 'WORKING_REMOTE'
    assert migrated_db.execute('SELECT end_time FROM geoattend.work_sessions').fetchone()['end_time'] is None
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_events').fetchone()['n'] == 1
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_requests').fetchone()['n'] == 1
