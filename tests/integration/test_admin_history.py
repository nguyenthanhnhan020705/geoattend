from datetime import datetime, timezone
from uuid import UUID, uuid4
import pytest
from tests.integration.test_attendance import employee, action
from tests.integration.test_office_attendance import configured, office_action
from tests.test_auth_api import signin

pytestmark = pytest.mark.integration


def as_admin(client):
    return {'X-CSRF-Token':signin(client).json()['csrf_token']}


def remove(client, headers, uid, day, **extra):
    return client.request('DELETE',f'/api/admin/users/{uid}/history/{day["id"]}',headers=headers,json={'expected_revision':day['revision'],'confirm_username':'worker',**extra})


def test_admin_views_other_employee_history_and_deletes_permanently(configured,migrated_db):
    client, headers, uid = configured
    key = str(uuid4())
    assert office_action(client,headers,request_id=key).status_code == 200
    assert action(client,headers,1,'CHECK_OUT',None).status_code == 200
    admin = as_admin(client)
    url = f'/api/admin/users/{uid}/history'
    response = client.get(url)
    assert response.status_code == 200
    day = response.json()['items'][0]
    assert day['sessions'][0]['location']['status'] == 'available'
    assert len(day['events']) == 2
    assert client.get(url+'?from=2026-10-15&to=2026-10-14').status_code == 422
    assert client.get(url+'?page=0').status_code == 422
    assert client.get(url+'?user_id=bad').status_code == 422
    assert remove(client,admin,uid,day).status_code == 200
    assert client.get(url).json()['total'] == 0
    assert remove(client,admin,uid,day).status_code == 200  # Lost DELETE response retry.
    for table in ('work_sessions','attendance_events','office_locations'):
        from psycopg import sql
        assert migrated_db.execute(sql.SQL('SELECT count(*) AS n FROM geoattend.{}').format(sql.Identifier(table))).fetchone()['n'] == 0
    migrated_db.commit()
    user_headers = {'X-CSRF-Token':signin(client,'worker','Worker1234').json()['csrf_token']}
    assert client.get('/api/attendance/history').json()['total'] == 0
    assert office_action(client,user_headers,request_id=key).json()['code'] == 'HISTORY_DELETED'
    assert action(client,user_headers,0).json()['code'] == 'STALE_REVISION'
    state = client.get('/api/attendance/status').json()
    assert state['status'] == 'NOT_STARTED' and state['revision'] == 3
    assert action(client,user_headers,3).status_code == 200
    assert client.get('/api/attendance/history').json()['total'] == 1
    as_admin(client)
    assert remove(client,as_admin(client),uid,day).status_code == 409  # Cannot delete new work via old modal.


@pytest.mark.parametrize('state',['WORKING_REMOTE','LUNCH_BREAK'])
def test_admin_cannot_delete_active_day(employee,state):
    client, headers, uid = employee
    assert action(client,headers).status_code == 200
    if state == 'LUNCH_BREAK':
        assert action(client,headers,1,'START_LUNCH',None).status_code == 200
    admin = as_admin(client)
    response = client.get(f'/api/admin/users/{uid}/history')
    assert response.status_code == 200
    day = response.json()['items'][0]
    result = remove(client,admin,uid,day)
    assert result.status_code == 409 and result.json()['code'] == 'ACTIVE_DAY'
    assert client.get(f'/api/admin/users/{uid}/history').json()['items'][0]['status'] == state


def test_admin_delete_permissions_confirmation_and_target_isolation(employee,migrated_db):
    client, headers, uid = employee
    action(client,headers); action(client,headers,1,'CHECK_OUT',None)
    personal = client.get('/api/attendance/history').json()['items'][0]
    assert client.get(f'/api/admin/users/{uid}/history').status_code == 403
    assert remove(client,headers,uid,personal).status_code == 403
    admin = as_admin(client)
    assert remove(client,{},uid,personal).status_code == 403
    assert remove(client,admin,uid,personal,confirm_username='someone-else').status_code == 422
    assert remove(client,admin,uid,personal,expected_revision=0).status_code == 409
    from app.accounts.service import create_user
    other = create_user(migrated_db,'other','Khác','Worker1234'); migrated_db.commit()
    assert remove(client,admin,other.id,personal,confirm_username='other').status_code == 404
    assert client.get(f'/api/admin/users/{uuid4()}/history').status_code == 404
    admin_id = client.get('/api/auth/me').json()['id']
    assert client.get(f'/api/admin/users/{admin_id}/history').status_code == 403
    assert len(client.get(f'/api/admin/users/{uid}/history').json()['items'][0]['sessions']) == 1


def test_inactive_employee_history_is_accessible_and_expired_gps_hidden(configured,migrated_db,monkeypatch):
    client, headers, uid = configured
    office_action(client,headers); action(client,headers,1,'CHECK_OUT',None)
    migrated_db.execute('UPDATE geoattend.profiles SET is_active=false WHERE id=%s',(uid,)); migrated_db.commit()
    admin = as_admin(client)
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,11,20,2,tzinfo=timezone.utc))
    # Keep the admin auth valid for this controlled clock jump only.
    migrated_db.execute("UPDATE geoattend.auth_sessions SET expires_at='2026-11-21' WHERE user_id=(SELECT id FROM geoattend.profiles WHERE role='ADMIN')"); migrated_db.commit()
    response = client.get(f'/api/admin/users/{uid}/history?from=2026-10-14&to=2026-10-14')
    assert response.status_code == 200
    day = response.json()['items'][0]
    assert day['sessions'][0]['location']['status'] == 'expired'
    assert 'latitude' not in response.text and 'accuracy_m' not in response.text
    assert remove(client,admin,uid,day).status_code == 200


def test_delete_failure_rolls_back_history_and_replay(configured,migrated_db):
    client, headers, uid = configured
    office_action(client,headers); action(client,headers,1,'CHECK_OUT',None)
    admin = as_admin(client)
    day = client.get(f'/api/admin/users/{uid}/history').json()['items'][0]
    migrated_db.execute("CREATE FUNCTION geoattend.fail_history_delete() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test failure' USING ERRCODE='08006'; END $$")
    migrated_db.execute('CREATE TRIGGER fail_history_delete BEFORE DELETE ON geoattend.work_sessions FOR EACH ROW EXECUTE FUNCTION geoattend.fail_history_delete()'); migrated_db.commit()
    assert remove(client,admin,uid,day).status_code == 503
    assert client.get(f'/api/admin/users/{uid}/history').json()['items'][0] == day
    for table, count in [('work_sessions',1),('attendance_events',2),('office_locations',1)]:
        from psycopg import sql
        assert migrated_db.execute(sql.SQL('SELECT count(*) AS n FROM geoattend.{}').format(sql.Identifier(table))).fetchone()['n'] == count
    assert not migrated_db.execute('SELECT bool_or(history_deleted) AS deleted FROM geoattend.attendance_requests').fetchone()['deleted']


def test_delete_one_day_keeps_other_dates_and_accounts(employee,migrated_db):
    client, headers, uid = employee
    assert action(client,headers,0,'FULL_DAY_LEAVE','Nghỉ ngày này').status_code == 200
    older = migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status,revision) VALUES(%s,'2026-10-13','MORNING_LEAVE',1) RETURNING id",(uid,)).fetchone()['id']
    migrated_db.execute("INSERT INTO geoattend.attendance_events(day_id,event_type,event_time,source,reason) VALUES(%s,'MORNING_LEAVE','2026-10-13 02:00+00','USER','Giữ ngày cũ')",(older,))
    migrated_db.commit()
    admin = as_admin(client)
    url = f'/api/admin/users/{uid}/history'
    items = client.get(url).json()['items']
    assert len(items) == 2
    assert remove(client,admin,uid,items[0]).status_code == 200
    retained = client.get(url).json()
    assert retained['total'] == 1 and retained['items'][0]['id'] == str(older)
    assert retained['items'][0]['events'][0]['reason'] == 'Giữ ngày cũ'
    assert client.get('/api/admin/users').json()['items'][0]['id'] == uid


@pytest.mark.parametrize('same_request',[True,False])
def test_delete_races_with_restart_or_delete(employee,migrated_db,test_dsn,same_request):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    import psycopg
    from psycopg.rows import dict_row
    from app.auth.models import AuthContext, Account
    from app.accounts.history_service import delete_day
    from app.accounts.schemas import DeleteHistoryInput
    from app.attendance.service import act
    from app.attendance.schemas import ActionInput
    from app.errors import ApiError
    client, headers, uid = employee
    action(client,headers); action(client,headers,1,'CHECK_OUT',None)
    as_admin(client)
    day = client.get(f'/api/admin/users/{uid}/history').json()['items'][0]
    admin = migrated_db.execute("SELECT * FROM geoattend.profiles WHERE role='ADMIN'").fetchone()
    auth = migrated_db.execute('SELECT * FROM geoattend.auth_sessions WHERE user_id=%s AND revoked_at IS NULL',(admin['id'],)).fetchone()
    context = AuthContext(Account.from_row(admin),auth['id'],auth['csrf_token']); migrated_db.commit()
    gate=Barrier(2)
    def work(delete):
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            gate.wait(10)
            try:
                if delete:
                    return delete_day(conn,context,UUID(uid),UUID(day['id']),DeleteHistoryInput(expected_revision=2,confirm_username='worker'))
                return act(conn,UUID(uid),ActionInput(request_id=uuid4(),expected_revision=2,expected_work_date='2026-10-14',action='START_REMOTE',reason='Phiên mới'))
            except ApiError as error:
                return error.code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(work,True),executor.submit(work,same_request)]
        results=[f.result(15) for f in futures]
    if same_request:
        assert all(isinstance(r,dict) and r.get('deleted') for r in results)
    else:
        assert results.count('STALE_REVISION') == 1
    count=migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions WHERE end_time IS NULL').fetchone()['n']
    assert count == (1 if any(isinstance(r,dict) and r.get('status')=='WORKING_REMOTE' for r in results) else 0)


def test_admin_delete_rechecks_revocation_after_wait(employee,test_dsn,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import psycopg
    from app.accounts import history_service
    client, headers, uid = employee
    action(client,headers); action(client,headers,1,'CHECK_OUT',None)
    admin = as_admin(client)
    day = client.get(f'/api/admin/users/{uid}/history').json()['items'][0]
    admin_id = client.get('/api/auth/me').json()['id']
    reached = Event(); original = history_service.lock_admin_target
    def marked(*args):
        reached.set(); return original(*args)
    monkeypatch.setattr(history_service,'lock_admin_target',marked)
    with psycopg.connect(test_dsn) as blocker:
        blocker.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE',(uid,))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(remove,client,admin,uid,day)
            assert reached.wait(10)
            blocker.execute('UPDATE geoattend.auth_sessions SET revoked_at=now() WHERE user_id=%s',(admin_id,)); blocker.commit()
            assert future.result(15).status_code == 401


def test_history_delete_with_runtime_role_and_migration_repeat(employee,migrated_db,test_dsn):
    from psycopg import sql
    from psycopg.rows import dict_row
    from psycopg.conninfo import make_conninfo
    import psycopg
    from pathlib import Path
    from app.db.migrations import grant_runtime, apply_migrations
    from app.auth.models import Account, AuthContext
    from app.accounts.history_service import history, delete_day
    from app.accounts.schemas import DeleteHistoryInput
    client, headers, uid = employee
    uid = UUID(uid)
    action(client,headers); action(client,headers,1,'CHECK_OUT',None)
    as_admin(client)
    admin_row = migrated_db.execute("SELECT * FROM geoattend.profiles WHERE role='ADMIN'").fetchone()
    auth_row = migrated_db.execute('SELECT * FROM geoattend.auth_sessions WHERE user_id=%s AND revoked_at IS NULL',(admin_row['id'],)).fetchone()
    context = AuthContext(Account.from_row(admin_row),auth_row['id'],auth_row['csrf_token'])
    role = 'history_runtime_'+uuid4().hex
    migrated_db.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    grant_runtime(migrated_db,role); migrated_db.commit()
    assert apply_migrations(migrated_db,Path('migrations')) == []
    migrated_db.commit()
    try:
        with psycopg.connect(make_conninfo(test_dsn,user=role),row_factory=dict_row) as conn:
            day = history(conn,context,uid,None,None,1,20)['items'][0]
            assert delete_day(conn,context,uid,day['id'],DeleteHistoryInput(expected_revision=day['revision'],confirm_username='worker'))['deleted']
            assert history(conn,context,uid,None,None,1,20)['total'] == 0
    finally:
        migrated_db.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
        migrated_db.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role))); migrated_db.commit()


@pytest.mark.parametrize('legacy',[False,True])
def test_deleted_replay_scrubs_action_times_and_legacy_results(employee,migrated_db,monkeypatch,legacy):
    client, headers, uid = employee
    key = str(uuid4())
    assert action(client,headers,request_id=key).status_code == 200
    assert action(client,headers,1,'CHECK_OUT',None).status_code == 200
    if legacy:
        # Simulate a valid pre-003 row: event UUIDs exist, replay columns were never backfilled.
        migrated_db.execute('UPDATE geoattend.attendance_requests SET result_work_date=NULL,result_session_id=NULL,result_status=NULL,result_revision=NULL WHERE request_id=%s',(key,)); migrated_db.commit()
    admin = as_admin(client)
    day = client.get(f'/api/admin/users/{uid}/history').json()['items'][0]
    deleted_at = datetime(2026,10,14,3,tzinfo=timezone.utc)
    monkeypatch.setattr('app.clock.utc_now',lambda:deleted_at)
    assert remove(client,admin,uid,day).status_code == 200
    rows = migrated_db.execute('SELECT * FROM geoattend.attendance_requests').fetchall()
    assert all(row['history_deleted'] and row['result_event_ids']==[] for row in rows)
    assert all(row['completed_at']==deleted_at for row in rows)
    assert all(row['result_session_id'] is None and row['result_work_date'] is None and row['result_status'] is None and row['result_revision'] is None for row in rows)
    migrated_db.commit()
    user_headers={'X-CSRF-Token':signin(client,'worker','Worker1234').json()['csrf_token']}
    assert action(client,user_headers,request_id=key).json()['code']=='HISTORY_DELETED'
