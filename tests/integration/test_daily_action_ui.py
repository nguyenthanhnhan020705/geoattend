from datetime import datetime, timezone
from uuid import uuid4
import pytest
from playwright.sync_api import expect
from tests.integration.test_attendance import employee, action
from tests.integration.test_office_attendance import configured, office_action
from tests.integration.test_browser import live_site
from tests.integration.test_office_browser import office_site
from tests.integration.test_phase4_browser import phase4_page

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('reason', [None, '', '   ', 'x'*1001])
def test_early_checkout_requires_reason_without_closing_session(employee,migrated_db,reason):
    client,headers,_=employee
    assert action(client,headers).status_code==200
    response=action(client,headers,1,'CHECK_OUT',reason)
    assert response.status_code==422
    status=client.get('/api/attendance/status').json()
    assert status['status']=='WORKING_REMOTE' and status['revision']==1
    assert status['open_session'] is not None
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_requests').fetchone()['n']==1
    assert migrated_db.execute("SELECT count(*) AS n FROM geoattend.attendance_events WHERE event_type='WORK_END'").fetchone()['n']==0


def test_lunch_progress_is_server_derived_and_resets_on_new_day(employee,monkeypatch):
    client, headers, _ = employee
    assert client.get('/api/attendance/status').json()['lunch_taken'] is False
    assert action(client,headers).status_code==200
    assert client.get('/api/attendance/status').json()['lunch_taken'] is False
    assert action(client,headers,1,'START_LUNCH',None).status_code==200
    assert client.get('/api/attendance/status').json()['lunch_taken'] is True
    assert action(client,headers,2).status_code==200
    assert client.get('/api/attendance/status').json()['lunch_taken'] is True
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,15,2,tzinfo=timezone.utc))
    assert client.get('/api/attendance/status').json()['lunch_taken'] is False


def test_prechange_checkout_without_reason_still_replays(employee,migrated_db):
    import hashlib
    import json
    client,headers,_=employee
    assert action(client,headers).status_code==200
    key=str(uuid4())
    original=action(client,headers,1,'CHECK_OUT','Old checkout',key)
    assert original.status_code==200
    # Reconstruct the persisted request and history produced before reasons
    # became mandatory. Use the literal old payload, not a production helper.
    payload={'expected_revision':1,'expected_work_date':'2026-10-14','action':'CHECK_OUT','reason':None}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    migrated_db.execute('UPDATE geoattend.attendance_requests SET payload_hash=%s WHERE request_id=%s',(digest,key))
    migrated_db.execute('UPDATE geoattend.work_sessions SET end_reason=NULL')
    migrated_db.execute("UPDATE geoattend.attendance_events SET reason=NULL WHERE event_type='WORK_END'")
    migrated_db.commit()
    replay=action(client,headers,1,'CHECK_OUT',None,key)
    assert replay.status_code==200 and replay.json()==original.json()
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_requests').fetchone()['n']==2
    assert action(client,headers,2).json()['code']=='DAY_FINISHED'


@pytest.mark.parametrize('lunch', [False, True])
@pytest.mark.parametrize('mode', ['OFFICE', 'REMOTE'])
def test_checkout_locks_day_server_side_and_replays_safely(configured,monkeypatch,migrated_db,lunch,mode):
    client, headers, _ = configured
    assert (office_action(client,headers) if mode=='OFFICE' else action(client,headers)).status_code==200
    revision=1
    if lunch:
        assert action(client,headers,1,'START_LUNCH',None).status_code==200
        assert action(client,headers,2).status_code==200
        revision=3
    key=str(uuid4())
    reason=None if lunch else '  Có việc gia đình  '
    end=action(client,headers,revision,'CHECK_OUT',reason,key)
    assert end.status_code==200
    for _ in range(2):
        status=client.get('/api/attendance/status').json()
        assert status['day_finished'] is True and status['allowed_actions']==[]
        assert status['lunch_taken'] is lunch and status['open_session'] is None
        assert action(client,headers,revision+1).json()['code']=='DAY_FINISHED'
        assert office_action(client,headers,revision+1).json()['code']=='DAY_FINISHED'
    assert action(client,headers,revision,'CHECK_OUT',reason,key).json()==end.json()
    if not lunch:
        assert migrated_db.execute('SELECT end_reason FROM geoattend.work_sessions').fetchone()['end_reason']=='Có việc gia đình'
        assert migrated_db.execute("SELECT reason FROM geoattend.attendance_events WHERE event_type='WORK_END'").fetchone()['reason']=='Có việc gia đình'
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==(2 if lunch else 1)
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,17,tzinfo=timezone.utc))
    fresh=client.get('/api/attendance/status').json()
    assert fresh['day_finished'] is False and fresh['status']=='NOT_STARTED'
    assert action(client,headers,0,expected_work_date='2026-10-15').status_code==200


@pytest.mark.browser
@pytest.mark.parametrize('mode', ['OFFICE', 'REMOTE'])
def test_early_checkout_hides_checkin_until_next_day(phase4_page,monkeypatch,migrated_db,mode):
    page=phase4_page
    if mode=='OFFICE':
        page.locator('#start-office').click()
    else:
        page.locator('#choose-remote').click()
        page.get_by_label('Lý do làm Remote').fill('Làm buổi sáng')
        page.locator('#remote-form button').click()
    expect(page.locator('#check-out')).to_have_text('CHECK-OUT SỚM')
    page.locator('#check-out').click()
    expect(page.get_by_label('Lý do Check-out sớm')).to_be_visible()
    expect(page.locator('#attendance-status')).to_contain_text('Đang làm')
    page.locator('#checkout-form button').click()
    expect(page.locator('#attendance-status')).to_contain_text('Đang làm')
    page.get_by_label('Lý do Check-out sớm').fill('   ')
    page.locator('#checkout-form button').click()
    expect(page.locator('#attendance-status')).to_contain_text('Đang làm')
    reason='<img src=x onerror=alert(1)>'
    page.get_by_label('Lý do Check-out sớm').fill(reason)
    page.locator('#close-reason').click()
    expect(page.locator('#check-out')).to_be_focused()
    page.locator('#check-out').click()
    expect(page.get_by_label('Lý do Check-out sớm')).to_have_value(reason)
    gps=page.evaluate('gpsCalls')
    calls=[]
    def lose_first(route):
        calls.append(route.request.post_data_json)
        if len(calls)==1: route.fetch();route.abort('failed')
        else: route.continue_()
    page.route('**/api/attendance/actions',lose_first)
    page.locator('#checkout-form button').click()
    expect(page.locator('#retry-action')).to_be_visible()
    assert page.evaluate('gpsCalls')==gps
    page.reload()
    page.locator('#retry-action').click()
    expect(page.locator('#retry-action')).to_be_hidden()
    assert calls[0]==calls[1] and calls[0]['reason']==reason
    assert migrated_db.execute("SELECT count(*) AS n FROM geoattend.attendance_events WHERE event_type='WORK_END'").fetchone()['n']==1
    page.locator('#personal-history summary').click()
    expect(page.locator('#history-list')).to_contain_text(reason)
    assert page.locator('#history-list img').count()==0
    for reload in (False, True):
        if reload: page.reload()
        expect(page.locator('#day-notice')).to_contain_text('ngày mai')
        expect(page.locator('#attendance-choices')).to_be_hidden()
        expect(page.locator('#start-lunch')).to_be_hidden()
        expect(page.locator('#check-out')).to_be_hidden()
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,17,tzinfo=timezone.utc))
    page.reload()
    expect(page.locator('#attendance-status')).to_have_text('Chưa bắt đầu')
    expect(page.locator('#start-office')).to_be_enabled()
    expect(page.locator('#choose-remote')).to_be_enabled()


@pytest.mark.browser
@pytest.mark.parametrize('first,second',[('OFFICE','OFFICE'),('OFFICE','REMOTE'),('REMOTE','OFFICE'),('REMOTE','REMOTE')])
def test_daily_buttons_follow_lunch_progress_after_reload(phase4_page,first,second):
    page=phase4_page
    if first=='OFFICE':
        page.locator('#start-office').click()
    else:
        page.locator('#choose-remote').click()
        page.get_by_label('Lý do làm Remote').fill('Buổi sáng')
        page.locator('#remote-form button').click()
    expect(page.locator('#attendance-status')).to_contain_text('Đang làm')
    expect(page.locator('.attendance-choices')).to_be_hidden()
    expect(page.locator('#reason-panel')).to_be_hidden()
    expect(page.locator('#start-lunch')).to_have_text('NGHỈ TRƯA')
    expect(page.locator('#check-out')).to_have_text('CHECK-OUT SỚM')
    page.reload()
    expect(page.locator('#check-out')).to_have_text('CHECK-OUT SỚM')
    expect(page.locator('.attendance-choices')).to_be_hidden()
    page.locator('#start-lunch').click()
    expect(page.locator('#attendance-status')).to_have_text('Đang nghỉ trưa')
    expect(page.locator('#start-office')).to_have_text('TIẾP TỤC OFFICE')
    expect(page.locator('#choose-remote')).to_have_text('TIẾP TỤC REMOTE')
    expect(page.locator('#start-office')).to_be_enabled()
    expect(page.locator('#choose-remote')).to_be_enabled()
    expect(page.locator('#choose-leave')).to_be_hidden()
    expect(page.locator('#start-lunch')).to_be_hidden()
    expect(page.locator('#check-out')).to_be_hidden()
    page.reload()
    expect(page.locator('#choose-remote')).to_have_text('TIẾP TỤC REMOTE')
    if second=='OFFICE':
        page.locator('#start-office').click()
    else:
        page.locator('#choose-remote').click()
        page.get_by_label('Lý do làm Remote').fill('Buổi chiều')
        page.locator('#remote-form button').click()
    expect(page.locator('#attendance-status')).to_contain_text('Đang làm')
    expect(page.locator('.attendance-choices')).to_be_hidden()
    expect(page.locator('#start-lunch')).to_be_hidden()
    expect(page.locator('#reason-panel')).to_be_hidden()
    expect(page.locator('#check-out')).to_have_text('CHECK-OUT')
    page.reload()
    expect(page.locator('#check-out')).to_have_text('CHECK-OUT')
    expect(page.locator('#start-lunch')).to_be_hidden()
    expect(page.locator('.attendance-choices')).to_be_hidden()
    page.locator('#check-out').click()
    expect(page.locator('#attendance-status')).to_have_text('Đã Check-out')
    expect(page.locator('#day-notice')).to_contain_text('ngày mai')
    expect(page.locator('.attendance-choices')).to_be_hidden()
    expect(page.locator('#check-out')).to_be_hidden()
    page.reload()
    expect(page.locator('#day-notice')).to_contain_text('ngày mai')
    expect(page.locator('.attendance-choices')).to_be_hidden()
