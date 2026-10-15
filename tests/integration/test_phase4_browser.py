from datetime import datetime, timezone
from pathlib import Path
import json
import os
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_office_browser import office_site
from tests.integration.test_office import POLYGON

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.fixture
def phase4_page(office_site,migrated_db):
    migrated_db.execute('INSERT INTO geoattend.office(name,address,geom,revision) VALUES(%s,%s,ST_GeomFromGeoJSON(%s),1)',('Office','HCM',json.dumps(POLYGON)))
    migrated_db.commit()
    with sync_playwright() as p:
        channel = os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge')
        browser = p.chromium.launch(channel=None if channel=='chromium' else channel,headless=True)
        page = browser.new_page(viewport={'width':360,'height':800})
        page.set_default_timeout(5000)
        errors = []
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.add_init_script("window.gpsCalls=0;window.gpsMode='inside';navigator.geolocation.getCurrentPosition=(ok,fail)=>{window.gpsCalls++;if(window.gpsMode==='denied')return fail({code:1});ok({coords:{latitude:window.gpsMode==='outside'?12:10.5,longitude:106.5,accuracy:10}})}")
        login(page,office_site,'worker','Worker1234')
        expect(page.locator('#attendance-status')).to_have_text('Chưa bắt đầu')
        yield page
        assert errors == []
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        browser.close()


def remote(page, button, reason='Làm ở nhà'):
    page.get_by_label('Lý do làm Remote').fill(reason)
    page.get_by_role('button',name=button,exact=True).click()
    expect(page.locator('#attendance-status')).to_have_text('Đang làm Remote')


def test_lunch_resume_and_switch_timeline(phase4_page,migrated_db):
    page = phase4_page
    remote(page,'Bắt đầu Remote')
    page.get_by_role('button',name='Nghỉ trưa',exact=True).click()
    expect(page.locator('#attendance-status')).to_have_text('Đang nghỉ trưa')
    expect(page.locator('#history-list')).to_contain_text('Nghỉ trưa')
    page.get_by_role('button',name='Tiếp tục Office',exact=True).click()
    expect(page.locator('#attendance-status')).to_have_text('Đang làm tại văn phòng')
    remote(page,'Chuyển sang Remote','Buổi chiều')
    page.get_by_role('button',name='Chuyển sang Office',exact=True).click()
    expect(page.locator('#attendance-status')).to_have_text('Đang làm tại văn phòng')
    page.get_by_role('button',name='Check-out',exact=True).click()
    expect(page.locator('#attendance-status')).to_have_text('Đã Check-out')
    expect(page.locator('#history-list')).to_contain_text('Buổi chiều')
    assert page.evaluate('gpsCalls') == 2
    rows = migrated_db.execute('SELECT end_time FROM geoattend.work_sessions').fetchall()
    assert len(rows) == 4 and all(r['end_time'] for r in rows)
    page.set_viewport_size({'width':1280,'height':900})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    artifacts = Path('.local-tests/phase-4/artifacts'); artifacts.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(artifacts/'timeline-desktop.png'),full_page=True)


@pytest.mark.parametrize('leave,label,next_button', [('MORNING_LEAVE','Nghỉ buổi sáng','Bắt đầu Remote'),('FULL_DAY_LEAVE','Nghỉ cả ngày','Hủy nghỉ và bắt đầu Remote')])
def test_leave_reason_and_cancel_history(phase4_page,leave,label,next_button):
    page = phase4_page
    reason = '<img src=x onerror=alert(1)>'
    page.get_by_label('Lý do nghỉ').fill(reason)
    page.get_by_role('button',name=label,exact=True).click()
    expect(page.locator('#attendance-status')).to_have_text(label)
    expect(page.locator('#history-list')).to_contain_text(reason)
    remote(page,next_button)
    page.reload()
    expect(page.locator('#attendance-status')).to_have_text('Đang làm Remote')
    expect(page.locator('#history-list')).to_contain_text(reason)
    assert page.locator('#history-list img').count() == 0 and page.evaluate('gpsCalls') == 0
    if leave == 'FULL_DAY_LEAVE':
        expect(page.locator('#history-list')).to_contain_text('Hủy nghỉ')


@pytest.mark.parametrize('office_action', ['cancel','switch','resume'])
def test_new_office_actions_retry_without_persisting_gps(phase4_page,migrated_db,office_action):
    page = phase4_page
    if office_action == 'cancel':
        page.get_by_label('Lý do nghỉ').fill('Nghỉ')
        page.get_by_role('button',name='Nghỉ cả ngày',exact=True).click()
        expect(page.locator('#attendance-status')).to_have_text('Nghỉ cả ngày')
        button = 'Hủy nghỉ và bắt đầu Office'; expected_sessions = 1
    else:
        remote(page,'Bắt đầu Remote')
        button = 'Chuyển sang Office'; expected_sessions = 2
        if office_action == 'resume':
            page.get_by_role('button',name='Nghỉ trưa',exact=True).click()
            expect(page.locator('#attendance-status')).to_have_text('Đang nghỉ trưa')
            button = 'Tiếp tục Office'
    page.evaluate("window.gpsMode='denied'")
    page.get_by_role('button',name=button,exact=True).click()
    expect(page.locator('#message')).to_contain_text('chưa cấp quyền')
    page.evaluate("window.gpsMode='inside'")
    calls = []
    def lose_first(route):
        calls.append(route.request.post_data_json)
        if len(calls)==1:
            route.fetch(); route.abort('failed')
        else:
            route.continue_()
    page.route('**/api/attendance/actions',lose_first)
    page.get_by_role('button',name=button,exact=True).click()
    expect(page.get_by_role('button',name='Gửi lại thao tác')).to_be_visible()
    assert page.evaluate('sessionStorage.getItem("geoattend.pendingAttendance")') is None
    assert page.evaluate('JSON.stringify(localStorage)') == '{}'
    page.get_by_role('button',name='Gửi lại thao tác').click()
    expect(page.get_by_role('button',name='Gửi lại thao tác')).to_be_hidden()
    expect(page.locator('#attendance-status')).to_have_text('Đang làm tại văn phòng')
    assert calls[0] == calls[1] and page.evaluate('gpsCalls') == 2
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n'] == expected_sessions


def test_leave_timeout_reload_retry_same_uuid(phase4_page,migrated_db):
    page = phase4_page
    page.add_init_script("const native=window.setTimeout;window.setTimeout=(fn,ms,...args)=>native(fn,ms===15000?300:ms,...args)")
    page.reload()
    expect(page.get_by_label('Lý do nghỉ')).to_be_visible()
    calls = []; held = []
    def hold_first(route):
        calls.append(route.request.post_data_json)
        if len(calls)==1:
            held.append(route)
            page.evaluate("document.documentElement.dataset.actionHeld='yes'")
        else:
            route.continue_()
    page.route('**/api/attendance/actions',hold_first)
    page.get_by_label('Lý do nghỉ').fill('Việc riêng')
    page.get_by_role('button',name='Nghỉ cả ngày',exact=True).click()
    expect(page.locator('html')).to_have_attribute('data-action-held','yes')
    expect(page.get_by_role('button',name='Nghỉ buổi sáng',exact=True)).to_be_disabled()
    expect(page.locator('#message')).to_contain_text('Chưa xác nhận')
    expect(page.get_by_role('button',name='Gửi lại thao tác')).to_be_enabled()
    saved = page.evaluate('JSON.parse(sessionStorage.getItem("geoattend.pendingAttendance"))')
    assert saved['body'] == calls[0]
    held[0].abort()
    page.reload()
    page.get_by_role('button',name='Gửi lại thao tác').click()
    expect(page.locator('#attendance-status')).to_have_text('Nghỉ cả ngày')
    assert calls[0] == calls[1]
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_events').fetchone()['n'] == 1


def test_lunch_day_end_system_label(phase4_page,monkeypatch):
    page = phase4_page
    remote(page,'Bắt đầu Remote')
    page.get_by_role('button',name='Nghỉ trưa',exact=True).click()
    expect(page.locator('#attendance-status')).to_have_text('Đang nghỉ trưa')
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13,tzinfo=timezone.utc))
    page.get_by_role('button',name='Làm mới',exact=True).click()
    expect(page.locator('#attendance-status')).to_have_text('Đã Check-out')
    expect(page.locator('#history-list')).to_contain_text('Hệ thống kết thúc ngày lúc 20:00')
