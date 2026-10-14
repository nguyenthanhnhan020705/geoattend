from datetime import datetime, timezone
from uuid import uuid4
import pytest
from tests.integration.test_attendance import employee, action

pytestmark=pytest.mark.integration


def set_time(monkeypatch,hour,minute=0,second=0,day=14):
    now=datetime(2026,10,day,hour,minute,second,tzinfo=timezone.utc)
    monkeypatch.setattr('app.clock.utc_now',lambda:now)
    return now


@pytest.mark.parametrize('second,accepted',[( -1,True),(0,False),(1,False)])
def test_cutoff_boundary(employee,monkeypatch,second,accepted):
    client,headers,_=employee
    if second==-1: set_time(monkeypatch,12,59,59)
    else: set_time(monkeypatch,13,0,second)
    response=action(client,headers)
    assert response.status_code==(200 if accepted else 409)


def test_late_read_and_rejected_action_commit_catchup(employee,migrated_db,monkeypatch):
    client,headers,_=employee
    assert action(client,headers).status_code==200
    recorded=set_time(monkeypatch,14)
    assert action(client,headers,1,'CHECK_OUT',None).status_code==409
    row=migrated_db.execute("SELECT end_time,end_source FROM geoattend.work_sessions").fetchone()
    assert row=={'end_time':datetime(2026,10,14,13,tzinfo=timezone.utc),'end_source':'SYSTEM'}
    event=migrated_db.execute("SELECT event_time,recorded_at FROM geoattend.attendance_events WHERE source='SYSTEM'").fetchone()
    assert event['event_time']==datetime(2026,10,14,13,tzinfo=timezone.utc)
    assert event['recorded_at']==recorded
    assert client.get('/api/attendance/status').json()['status']=='CHECKED_OUT'
    assert client.get('/api/attendance/status').json()['allowed_actions']==[]
    assert migrated_db.execute("SELECT count(*) AS n FROM geoattend.attendance_events WHERE source='SYSTEM'").fetchone()['n']==1


def test_next_day_closes_previous_before_new_session(employee,migrated_db,monkeypatch):
    client,headers,_=employee
    assert action(client,headers).status_code==200
    set_time(monkeypatch,2,day=15)
    new=action(client,headers)
    assert new.status_code==200
    rows=migrated_db.execute('SELECT work_date,status FROM geoattend.attendance_days ORDER BY work_date').fetchall()
    assert [r['status'] for r in rows]==['CHECKED_OUT','WORKING_REMOTE']
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions WHERE end_time IS NULL').fetchone()['n']==1


def test_replay_after_deadline_returns_original_result(employee,monkeypatch):
    client,headers,_=employee
    key=str(uuid4())
    first=action(client,headers,request_id=key)
    set_time(monkeypatch,14)
    assert action(client,headers,request_id=key).json()==first.json()
    assert client.get('/api/attendance/status').json()['status']=='CHECKED_OUT'


def test_maintenance_lunch_and_leave_rules(employee,migrated_db,monkeypatch):
    from app.accounts.service import create_user
    from app.attendance.service import maintain
    client,headers,uid=employee
    assert action(client,headers).status_code==200
    migrated_db.execute("UPDATE geoattend.work_sessions SET end_time='2026-10-14 05:00Z',end_source='USER'")
    migrated_db.execute("UPDATE geoattend.attendance_days SET status='LUNCH_BREAK'")
    for name,state in [('morning','MORNING_LEAVE'),('full','FULL_DAY_LEAVE'),('none','NOT_STARTED')]:
        user=create_user(migrated_db,name,name,'User12345')
        migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,'2026-10-14',%s)",(user.id,state))
    migrated_db.commit()
    set_time(monkeypatch,14)
    assert maintain(migrated_db)==1
    assert maintain(migrated_db)==0
    assert migrated_db.execute('SELECT end_time FROM geoattend.work_sessions').fetchone()['end_time']==datetime(2026,10,14,5,tzinfo=timezone.utc)
    assert migrated_db.execute("SELECT event_type FROM geoattend.attendance_events WHERE source='SYSTEM'").fetchone()['event_type']=='DAY_END'
    states={r['status'] for r in migrated_db.execute('SELECT status FROM geoattend.attendance_days')}
    assert states=={'CHECKED_OUT','MORNING_LEAVE','FULL_DAY_LEAVE','NOT_STARTED'}


def test_maintenance_once_cli(employee,test_dsn):
    import os,subprocess,sys
    client,headers,_=employee
    assert action(client,headers).status_code==200
    env=os.environ.copy(); env['GEOATTEND_DATABASE_URL']=test_dsn
    completed=subprocess.run([sys.executable,'-m','scripts.maintenance','--once'],env=env,capture_output=True,encoding='utf-8')
    assert completed.returncode==0,completed.stderr
    assert 'Maintenance' in completed.stdout
