from datetime import datetime, timezone
from uuid import uuid4
import pytest
from playwright.sync_api import expect
from tests.integration.test_attendance import employee, action
from tests.integration.test_office_attendance import configured, office_action
from tests.integration.test_phase4_browser import phase4_page
from tests.integration.test_browser import live_site
from tests.integration.test_office_browser import office_site

pytestmark=pytest.mark.integration


def test_prechange_cancel_leave_uuid_still_replays(employee,migrated_db):
    import hashlib
    import json
    client,headers,uid=employee
    assert action(client,headers,0,'FULL_DAY_LEAVE','Nghỉ').status_code==200
    day=migrated_db.execute('SELECT id FROM geoattend.attendance_days').fetchone()['id']
    # Persist the historical result of a cancellation committed under the old
    # policy. No new cancellation is accepted by today's production path.
    session=migrated_db.execute("INSERT INTO geoattend.work_sessions(day_id,work_mode,start_time,start_reason) VALUES(%s,'REMOTE','2026-10-14 02:00+00','Legacy remote') RETURNING id",(day,)).fetchone()['id']
    events=[]
    for kind,sid,reason in [('LEAVE_CANCELLED',None,None),('WORK_START',session,'Legacy remote')]:
        events.append(migrated_db.execute("INSERT INTO geoattend.attendance_events(day_id,session_id,event_type,event_time,recorded_at,source,reason) VALUES(%s,%s,%s,'2026-10-14 02:00+00','2026-10-14 02:00+00','USER',%s) RETURNING id",(day,sid,kind,reason)).fetchone()['id'])
    migrated_db.execute("UPDATE geoattend.attendance_days SET status='WORKING_REMOTE',revision=2 WHERE id=%s",(day,))
    key=str(uuid4())
    payload={'expected_revision':1,'expected_work_date':'2026-10-14','action':'CANCEL_LEAVE_START_REMOTE','reason':'Legacy remote'}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    migrated_db.execute("INSERT INTO geoattend.attendance_requests(user_id,request_id,payload_hash,result_event_ids,completed_at,result_status,result_revision,result_work_date,result_session_id) VALUES(%s,%s,%s,%s,'2026-10-14 02:00+00','WORKING_REMOTE',2,'2026-10-14',%s)",(uid,key,digest,events,session))
    migrated_db.commit()
    replay=action(client,headers,1,'CANCEL_LEAVE_START_REMOTE','Legacy remote',key)
    assert replay.status_code==200
    assert replay.json()['event_ids']==[str(event) for event in events]
    assert replay.json()['session_id']==str(session) and replay.json()['revision']==2
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==1
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_requests').fetchone()['n']==2


@pytest.mark.parametrize('mode',['OFFICE','REMOTE'])
def test_morning_leave_resumes_afternoon_then_final_checkout(configured,mode,migrated_db):
    client,headers,_=configured
    assert action(client,headers,0,'MORNING_LEAVE','Có việc sáng').status_code==200
    assert (office_action(client,headers,1) if mode=='OFFICE' else action(client,headers,1)).status_code==200
    status=client.get('/api/attendance/status').json()
    assert status['morning_leave'] is True and status['lunch_taken'] is False
    assert action(client,headers,2,'CHECK_OUT',None).status_code==200
    assert client.get('/api/attendance/status').json()['day_finished'] is True
    assert action(client,headers,3).json()['code']=='DAY_FINISHED'
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==1


def test_full_day_leave_finishes_day_and_replays(configured,monkeypatch,migrated_db):
    client,headers,_=configured
    key=str(uuid4())
    saved=action(client,headers,0,'FULL_DAY_LEAVE','Nghỉ hôm nay',key)
    assert saved.status_code==200
    status=client.get('/api/attendance/status').json()
    assert status['status']=='FULL_DAY_LEAVE' and status['day_finished'] is True
    assert status['allowed_actions']==[] and status['open_session'] is None
    for kind in ('START_REMOTE','CANCEL_LEAVE_START_REMOTE'):
        rejected=action(client,headers,1,kind,'Quay lại')
        assert rejected.status_code==409 and rejected.json()['code']=='DAY_FINISHED'
    assert office_action(client,headers,1).json()['code']=='DAY_FINISHED'
    assert action(client,headers,0,'FULL_DAY_LEAVE','Nghỉ hôm nay',key).json()==saved.json()
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==0
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,17,tzinfo=timezone.utc))
    assert client.get('/api/attendance/status').json()['day_finished'] is False


@pytest.mark.browser
@pytest.mark.parametrize('leave',['morning','full'])
@pytest.mark.parametrize('mode',['OFFICE','REMOTE'])
def test_user_selects_leave_then_reason_and_follows_day_flow(phase4_page,leave,mode):
    page=phase4_page
    page.locator('#choose-leave').click()
    expect(page.get_by_label('Lý do nghỉ')).to_be_hidden()
    page.locator('#morning-leave' if leave=='morning' else '#full-day-leave').click()
    expect(page.get_by_label('Lý do nghỉ')).to_be_focused()
    page.get_by_label('Lý do nghỉ').fill('Có việc riêng')
    page.locator('#confirm-leave').click()
    if leave=='full':
        expect(page.locator('#attendance-status')).to_have_text('Nghỉ cả ngày')
        page.reload()
        expect(page.locator('#attendance-choices')).to_be_hidden()
        expect(page.locator('#day-notice')).to_contain_text('ngày mai',timeout=10000)
        return
    expect(page.locator('#attendance-status')).to_have_text('Đang nghỉ buổi sáng')
    page.reload()
    expect(page.locator('#start-office')).to_have_text('TIẾP TỤC BUỔI CHIỀU OFFICE')
    expect(page.locator('#choose-remote')).to_have_text('TIẾP TỤC BUỔI CHIỀU REMOTE')
    expect(page.locator('#choose-leave')).to_be_hidden()
    if mode=='OFFICE': page.locator('#start-office').click()
    else:
        page.locator('#choose-remote').click()
        page.get_by_label('Lý do làm Remote').fill('Làm buổi chiều')
        page.locator('#remote-form button').click()
    expect(page.locator('#attendance-status')).to_contain_text('Đang làm việc')
    page.reload()
    expect(page.locator('#check-out')).to_have_text('CHECK-OUT')
    expect(page.locator('#start-lunch')).to_be_hidden()
    page.locator('#check-out').click()
    expect(page.locator('#day-notice')).to_contain_text('ngày mai',timeout=10000)
