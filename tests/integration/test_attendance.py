from datetime import datetime, timezone
from uuid import uuid4
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def employee(api_client, monkeypatch):
    from tests.test_auth_api import signin
    csrf = signin(api_client).json()['csrf_token']
    response = api_client.post('/api/admin/users', headers={'X-CSRF-Token': csrf}, json={'username':'worker','full_name':'Nhân viên','password':'Worker1234'})
    assert response.status_code == 201
    csrf = signin(api_client,'worker','Worker1234').json()['csrf_token']
    # Inject only the clock; API, transactions and PostgreSQL stay real.
    monkeypatch.setattr('app.clock.utc_now', lambda:datetime(2026,10,14,2,tzinfo=timezone.utc))
    return api_client, {'X-CSRF-Token':csrf}, response.json()['id']


def action(client, headers, revision=0, kind='START_REMOTE', reason='Làm việc tại nhà', request_id=None, **extra):
    body = dict(request_id=request_id or str(uuid4()), expected_revision=revision, action=kind, **extra)
    if reason is not None:
        body['reason'] = reason
    return client.post('/api/attendance/actions', headers=headers, json=body)


def test_remote_checkout_restart_persisted(employee,migrated_db):
    client,headers,_ = employee
    first = action(client,headers)
    assert first.status_code == 200
    assert first.json()['status'] == 'WORKING_REMOTE'
    assert client.get('/api/attendance/status').json()['revision'] == 1
    end = action(client,headers,1,'CHECK_OUT',None)
    assert end.status_code == 200 and end.json()['status']=='CHECKED_OUT'
    again = action(client,headers,2)
    assert again.status_code == 200
    rows = migrated_db.execute('SELECT start_reason,end_source,end_time FROM geoattend.work_sessions ORDER BY start_time,id').fetchall()
    assert len(rows)==2
    assert sum(r['end_time'] is None for r in rows)==1
    assert next(r for r in rows if r['end_time'] is not None)['end_source']=='USER'
    assert client.get('/api/attendance/status').json()['open_session']['work_mode']=='REMOTE'


@pytest.mark.parametrize('reason',[None,'','   ','x'*1001])
def test_remote_reason_required(employee,reason):
    client,headers,_=employee
    response=action(client,headers,reason=reason)
    assert response.status_code==422
    assert client.get('/api/attendance/status').json()['status']=='NOT_STARTED'


@pytest.mark.parametrize('extra',[{'latitude':10},{'user_id':str(uuid4())},{'expected_revision':-1}])
def test_reject_extra_and_invalid_input(employee,extra):
    client,headers,_=employee
    body={'request_id':str(uuid4()),'expected_revision':0,'action':'START_REMOTE','reason':'Home'}
    body.update(extra)
    assert client.post('/api/attendance/actions',headers=headers,json=body).status_code==422


def test_replay_conflict_and_stale_revision(employee,migrated_db):
    client,headers,_=employee
    key=str(uuid4())
    first=action(client,headers,request_id=key)
    assert first.status_code==200
    assert action(client,headers,request_id=key).json()==first.json()
    assert action(client,headers,reason='Different',request_id=key).status_code==409
    assert action(client,headers,0,'CHECK_OUT',None).status_code==409
    assert action(client,headers,1).status_code==409
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==1


def test_history_ownership_and_pagination(employee,migrated_db):
    from app.accounts.service import create_user
    client,headers,uid=employee
    assert action(client,headers).status_code==200
    other=create_user(migrated_db,'other','Người khác','Other1234')
    migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,'2026-10-14','FULL_DAY_LEAVE')",(other.id,))
    migrated_db.commit()
    response=client.get('/api/attendance/history?from=2026-10-14&to=2026-10-14')
    assert response.status_code==200
    data=response.json()
    assert data['total']==1 and len(data['items'])==1
    assert data['items'][0]['events'][0]['reason']=='Làm việc tại nhà'
    assert 'Người khác' not in response.text and str(other.id) not in response.text
    assert client.get('/api/attendance/history?page=2&page_size=1').json()['items']==[]
    assert client.get('/api/attendance/history?from=2026-10-15&to=2026-10-14').status_code==422
    assert client.get('/api/attendance/history?page_size=101').status_code==422
    assert client.get('/api/attendance/history?user_id='+str(other.id)).status_code==422
    assert response.headers['cache-control']=='no-store'


def test_attendance_permissions_and_csrf(api_client):
    from tests.test_auth_api import signin
    assert api_client.get('/api/attendance/status').status_code==401
    csrf=signin(api_client).json()['csrf_token']
    assert api_client.get('/api/attendance/status').status_code==403
    assert api_client.get('/api/attendance/history').status_code==403
    assert action(api_client,{'X-CSRF-Token':csrf}).status_code==403


def test_missing_csrf_and_checkout_without_session(employee):
    client,headers,_=employee
    assert action(client,{}).status_code==403
    assert action(client,headers,kind='CHECK_OUT',reason=None).status_code==409


def test_transaction_rollback_on_event_failure(employee,migrated_db):
    client,headers,_=employee
    migrated_db.execute("CREATE FUNCTION geoattend.fail_event() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test failure' USING ERRCODE='08006'; END $$")
    migrated_db.execute('CREATE TRIGGER fail_event BEFORE INSERT ON geoattend.attendance_events FOR EACH ROW EXECUTE FUNCTION geoattend.fail_event()')
    migrated_db.commit()
    assert action(client,headers).status_code==503
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==0
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_requests').fetchone()['n']==0
    assert client.get('/api/attendance/status').json()['revision']==0
