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


def test_final_checkout_locks_day_server_side_and_replays_safely(configured,monkeypatch):
    client, headers, _ = configured
    assert action(client,headers).status_code==200
    assert action(client,headers,1,'START_LUNCH',None).status_code==200
    assert action(client,headers,2).status_code==200
    key=str(uuid4())
    end=action(client,headers,3,'CHECK_OUT',None,key)
    assert end.status_code==200
    for _ in range(2):
        status=client.get('/api/attendance/status').json()
        assert status['day_finished'] is True and status['allowed_actions']==[]
        assert action(client,headers,4).json()['code']=='DAY_FINISHED'
        assert office_action(client,headers,4).json()['code']=='DAY_FINISHED'
    assert action(client,headers,3,'CHECK_OUT',None,key).json()==end.json()
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,15,2,tzinfo=timezone.utc))
    fresh=client.get('/api/attendance/status').json()
    assert fresh['day_finished'] is False and fresh['status']=='NOT_STARTED'
    assert action(client,headers,0,expected_work_date='2026-10-15').status_code==200


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
