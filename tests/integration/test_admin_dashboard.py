from datetime import datetime, timezone
import pytest
from tests.integration.test_attendance import employee, action
from tests.test_auth_api import signin

pytestmark = pytest.mark.integration
STATUSES = ('NOT_STARTED','WORKING_OFFICE','WORKING_REMOTE','LUNCH_BREAK','MORNING_LEAVE','FULL_DAY_LEAVE','CHECKED_OUT')


def test_dashboard_permissions(employee):
    client, _, _ = employee
    assert client.get('/api/admin/dashboard').status_code == 403
    signin(client)
    response = client.get('/api/admin/dashboard')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert not any(secret in response.text for secret in ('password','token','csrf','session_id'))
    client.cookies.clear()
    assert client.get('/api/admin/dashboard').status_code == 401


def test_dashboard_all_users_counts_and_seven_states(employee,migrated_db):
    from app.accounts.service import create_user
    client, _, uid = employee
    for index, state in enumerate(STATUSES[1:]):
        user = create_user(migrated_db,f'person{index}',f'Người {index}','Worker1234')
        day = migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,'2026-10-14',%s) RETURNING id",(user.id,state)).fetchone()['id']
        if state.startswith('WORKING_'):
            migrated_db.execute("INSERT INTO geoattend.work_sessions(day_id,work_mode,start_time) VALUES(%s,%s,'2026-10-14 01:00+00')",(day,state.removeprefix('WORKING_')))
    migrated_db.execute('UPDATE geoattend.profiles SET is_active=false WHERE id=%s',(uid,))
    migrated_db.commit()
    signin(client)
    data = client.get('/api/admin/dashboard').json()
    assert data['total_users'] == 7 == len(data['items']) == sum(data['counts'].values())
    assert data['counts'] == dict.fromkeys(STATUSES,1)
    assert data['work_date'] == '2026-10-14'
    assert data['as_of'] == '2026-10-14T02:00:00Z'
    worker = next(item for item in data['items'] if item['id']==uid)
    assert worker == dict(id=uid,username='worker',full_name='Nhân viên',is_active=False,status='NOT_STARTED',open_session=None)
    for state in STATUSES:
        assert len([item for item in data['items'] if item['status']==state]) == data['counts'][state]


@pytest.mark.parametrize('lunch,hour,minute,want',[(False,12,59,'WORKING_REMOTE'),(False,13,0,'CHECKED_OUT'),(False,13,1,'CHECKED_OUT'),(False,17,0,'NOT_STARTED'),(True,12,59,'LUNCH_BREAK'),(True,13,0,'CHECKED_OUT'),(True,13,1,'CHECKED_OUT'),(True,17,0,'NOT_STARTED')])
def test_dashboard_catches_up_without_worker(employee,migrated_db,monkeypatch,lunch,hour,minute,want):
    client, headers, _ = employee
    assert action(client,headers).status_code == 200
    if lunch:
        assert action(client,headers,1,'START_LUNCH',None).status_code==200
    signin(client)
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,hour,minute,tzinfo=timezone.utc))
    for _ in range(2):
        response = client.get('/api/admin/dashboard')
        assert response.status_code == 200
        assert response.json()['items'][0]['status'] == want
    count = migrated_db.execute("SELECT count(*) AS n FROM geoattend.attendance_events WHERE source='SYSTEM'").fetchone()['n']
    assert count == (0 if hour==12 else 1)


def test_dashboard_cancelled_leave_and_deleted_today(employee):
    client, headers, uid = employee
    assert action(client,headers,0,'FULL_DAY_LEAVE','Nghỉ').status_code == 200
    assert action(client,headers,1,'CANCEL_LEAVE_START_REMOTE','Trở lại').status_code == 200
    assert action(client,headers,2,'CHECK_OUT','Personal appointment').status_code == 200
    csrf = signin(client).json()['csrf_token']
    data=client.get('/api/admin/dashboard').json()
    assert data['counts']['FULL_DAY_LEAVE']==0 and data['counts']['CHECKED_OUT']==1
    day=client.get(f'/api/admin/users/{uid}/history').json()['items'][0]
    assert client.request('DELETE',f'/api/admin/users/{uid}/history/{day["id"]}',headers={'X-CSRF-Token':csrf},json={'expected_revision':day['revision'],'confirm_username':'worker'}).status_code==200
    assert client.get('/api/admin/dashboard').json()['counts']['NOT_STARTED']==1


def test_dashboard_rechecks_session_after_wait(employee,test_dsn,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import psycopg
    from app.admin import service
    client, _, uid = employee
    signin(client)
    admin_id = client.get('/api/auth/me').json()['id']
    reached = Event()
    original = service.lock_profiles
    def marked(*args):
        reached.set()
        return original(*args)
    monkeypatch.setattr(service,'lock_profiles',marked)
    with psycopg.connect(test_dsn) as blocker:
        blocker.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE',(uid,))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(client.get,'/api/admin/dashboard')
            assert reached.wait(10)
            blocker.execute('UPDATE geoattend.auth_sessions SET revoked_at=now() WHERE user_id=%s',(admin_id,))
            blocker.commit()
            assert future.result(15).status_code==401


@pytest.mark.parametrize('operation',['action','delete'])
def test_dashboard_waits_for_atomic_employee_change(employee,migrated_db,test_dsn,monkeypatch,operation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import psycopg
    from psycopg.rows import dict_row
    from app.admin import service
    from app.attendance.service import act
    from app.attendance.schemas import ActionInput
    from app.accounts.history_service import delete_day
    from app.accounts.schemas import DeleteHistoryInput
    from app.auth.models import Account, AuthContext
    from uuid import UUID, uuid4
    client, headers, uid = employee
    if operation=='delete':
        action(client,headers); action(client,headers,1,'CHECK_OUT','Personal appointment')
    signin(client)
    profile=migrated_db.execute("SELECT * FROM geoattend.profiles WHERE role='ADMIN'").fetchone()
    session=migrated_db.execute('SELECT * FROM geoattend.auth_sessions WHERE user_id=%s AND revoked_at IS NULL',(profile['id'],)).fetchone()
    context=AuthContext(Account.from_row(profile),session['id'],session['csrf_token'])
    day=migrated_db.execute('SELECT * FROM geoattend.attendance_days WHERE user_id=%s',(uid,)).fetchone()
    migrated_db.commit()
    reached=Event(); original=service.lock_profiles
    def marked(*args):
        reached.set(); return original(*args)
    monkeypatch.setattr(service,'lock_profiles',marked)
    with psycopg.connect(test_dsn,row_factory=dict_row) as writer:
        # Hold the same ordered profile locks as the production operation.
        writer.execute('SELECT id FROM geoattend.profiles ORDER BY id FOR UPDATE').fetchall()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(client.get,'/api/admin/dashboard')
            assert reached.wait(10)
            if operation=='action':
                act(writer,UUID(uid),ActionInput(request_id=uuid4(),expected_revision=0,expected_work_date='2026-10-14',action='START_REMOTE',reason='Concurrent'))
            else:
                delete_day(writer,context,UUID(uid),day['id'],DeleteHistoryInput(expected_revision=2,confirm_username='worker'))
            writer.commit()
            response=future.result(15)
    assert response.status_code==200
    data=response.json()
    want='WORKING_REMOTE' if operation=='action' else 'NOT_STARTED'
    assert data['items'][0]['status']==want and data['counts'][want]==1
    assert sum(data['counts'].values())==data['total_users']==1
