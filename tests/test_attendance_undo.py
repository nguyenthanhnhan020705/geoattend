"""Exercise the real attendance page; replace only the HTTP API boundary."""
import functools
import http.server
import threading
import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright, expect


pytestmark = pytest.mark.browser


@pytest.fixture(params=['same-origin', 'pages'])
def undo_page(request, tmp_path):
    root = Path('app').resolve() if request.param=='same-origin' else tmp_path
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    origin = f'http://127.0.0.1:{server.server_port}'
    if request.param == 'pages':
        from scripts.build_pages import build_pages
        build_pages(tmp_path/'geoattend', base_path='/geoattend/', api_origin=origin,
                    version='undo-test', allow_loopback=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width':360, 'height':800})
        page.add_init_script("window.gpsCalls=0;navigator.geolocation.getCurrentPosition=(ok)=>{window.gpsCalls++;ok({coords:{latitude:10.5,longitude:106.5,accuracy:10}})}")
        if request.param == 'pages':
            key = f'geoattend:{origin}:/geoattend/:session'
            session = json.dumps(dict(token='a'*32, expiresAt='2099-01-01T00:00:00Z'))
            page.add_init_script(f'sessionStorage.setItem({json.dumps(key)}, {json.dumps(session)})')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        calls = []
        status = dict(work_date='2026-10-22', status='WORKING_REMOTE', revision=1,
                      open_session=dict(start_time='2026-10-22T02:00:00Z', start_reason='Ở nhà'),
                      server_time='2026-10-22T03:00:00Z', allowed_actions=['CHECK_OUT','START_LUNCH'],
                      lunch_taken=False, morning_leave=False, day_finished=False)

        def api(route):
            path = route.request.url.split('/api/')[1].split('?')[0]
            if path == 'auth/me':
                data = dict(id='worker', full_name='Nhân viên', username='worker', role='USER', csrf_token='csrf')
            elif path == 'attendance/status':
                data = status
            elif path == 'attendance/actions':
                body = route.request.post_data_json
                calls.append(body)
                state = {'START_LUNCH':'LUNCH_BREAK', 'CHECK_OUT':'CHECKED_OUT',
                         'START_OFFICE':'WORKING_OFFICE', 'START_REMOTE':'WORKING_REMOTE',
                         'MORNING_LEAVE':'MORNING_LEAVE', 'FULL_DAY_LEAVE':'FULL_DAY_LEAVE'}[body['action']]
                working = state.startswith('WORKING_')
                status.update(status=state, revision=status['revision']+1,
                              open_session=dict(start_time='2026-10-22T03:00:00Z',start_reason=body.get('reason')) if working else None,
                              allowed_actions=['CHECK_OUT','START_LUNCH'] if working else [],
                              day_finished=state in ('CHECKED_OUT','FULL_DAY_LEAVE'))
                data = dict(status=status['status'], revision=2)
            elif path == 'attendance/history':
                data = dict(items=[], total=0, page=1, page_size=20)
            else:
                route.fulfill(status=503, json=dict(code='REPORTS_UNAVAILABLE', message='Chưa kích hoạt'))
                return
            route.fulfill(json=data)

        page.route('**/api/**', api)
        page.goto(origin + ('/static/user.html' if request.param=='same-origin' else '/geoattend/user/'))
        expect(page.locator('#start-lunch')).to_be_enabled()
        page.clock.install()
        page.clock.pause_at(page.evaluate('(Date.now() + 1000) / 1000'))
        yield page, calls, status
        assert errors == []
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        browser.close()
    server.shutdown()
    server.server_close()
    thread.join()


def choose_action(page, action):
    if action == 'lunch':
        page.locator('#start-lunch').click()
    else:
        page.locator('#check-out').click()
        if action == 'early':
            page.locator('#checkout-reason').fill('Có việc gia đình')
            page.locator('#checkout-form button').click()


@pytest.mark.parametrize('action', ['lunch', 'early', 'checkout'])
def test_undo_cancels_without_sending(undo_page, action):
    page, calls, status = undo_page
    if action == 'checkout':
        status.update(lunch_taken=True)
        page.locator('#refresh-status').click()
        expect(page.locator('#check-out')).to_have_text('CHECK-OUT')
    choose_action(page, action)
    expect(page.locator('#undo-countdown')).to_contain_text('5')
    assert calls == []
    expect(page.locator('#start-lunch')).to_be_disabled()
    expect(page.locator('#check-out')).to_be_disabled()
    expect(page.locator('#retry-action')).to_be_hidden()
    page.clock.run_for(2000)
    expect(page.locator('#undo-countdown')).to_contain_text('3')
    page.get_by_role('button', name='Hoàn tác', exact=True).click()
    page.clock.run_for(6000)
    assert calls == []
    expect(page.locator('#attendance-status')).to_have_text('Đang làm Remote')
    expect(page.locator('#check-out')).to_be_enabled()


@pytest.mark.parametrize('action', ['lunch', 'early', 'checkout'])
def test_records_once_only_after_five_seconds(undo_page, action):
    page, calls, status = undo_page
    if action == 'checkout':
        status.update(lunch_taken=True)
        page.locator('#refresh-status').click()
        expect(page.locator('#check-out')).to_have_text('CHECK-OUT')
    choose_action(page, action)
    page.clock.run_for(4999)
    assert calls == []
    page.clock.run_for(1)
    expect(page.locator('#attendance-status')).to_have_text('Đang nghỉ trưa' if action=='lunch' else 'Đã Check-out')
    page.clock.run_for(6000)
    assert len(calls) == 1
    assert calls[0]['action'] == ('START_LUNCH' if action=='lunch' else 'CHECK_OUT')
    if action == 'early':
        assert calls[0]['reason'] == 'Có việc gia đình'


@pytest.mark.parametrize('navigation', ['reload', 'history'])
def test_leaving_cancels_unsent_action(undo_page, navigation):
    page, calls, _ = undo_page
    choose_action(page, 'lunch')
    expect(page.locator('#undo-action')).to_be_visible()
    if navigation == 'reload':
        page.reload()
    else:
        page.evaluate("location.hash = '#history'")
    page.clock.run_for(6000)
    assert calls == []
    expect(page.locator('#retry-action')).to_be_hidden()


def test_network_retry_keeps_original_request_without_another_countdown(undo_page):
    page, calls, _ = undo_page

    def lose_first(route):
        if not calls:
            calls.append(route.request.post_data_json)
            route.abort('failed')
        else:
            route.fallback()

    page.route('**/api/attendance/actions', lose_first)
    choose_action(page, 'early')
    page.clock.run_for(5000)
    expect(page.locator('#retry-action')).to_be_visible()
    expect(page.locator('#undo-action')).to_be_hidden()
    page.reload()
    page.locator('#retry-action').click()
    expect(page.locator('#attendance-status')).to_have_text('Đã Check-out')
    assert len(calls) == 2
    assert calls[0] == calls[1]


def test_system_clock_change_does_not_shorten_undo_window(undo_page):
    page, calls, _ = undo_page
    choose_action(page, 'lunch')
    page.clock.set_system_time(page.evaluate('(Date.now() + 3600000) / 1000'))
    page.clock.run_for(1000)
    assert calls == []
    expect(page.locator('#undo-countdown')).to_contain_text('4')
    page.get_by_role('button', name='Hoàn tác', exact=True).click()


@pytest.mark.parametrize('initial,action,label,focused', [
    ('NOT_STARTED','START_OFFICE','Check-in Office','start-office'),
    ('NOT_STARTED','START_REMOTE','Check-in Remote','remote-reason'),
    ('NOT_STARTED','MORNING_LEAVE','Nghỉ buổi sáng','leave-reason'),
    ('NOT_STARTED','FULL_DAY_LEAVE','Nghỉ cả ngày','leave-reason'),
    ('LUNCH_BREAK','START_OFFICE','Tiếp tục Office','start-office'),
    ('LUNCH_BREAK','START_REMOTE','Tiếp tục Remote','remote-reason'),
    ('MORNING_LEAVE','START_OFFICE','Tiếp tục buổi chiều Office','start-office'),
    ('MORNING_LEAVE','START_REMOTE','Tiếp tục buổi chiều Remote','remote-reason'),
])
def test_all_attendance_actions_allow_undo_before_recording(undo_page, initial, action, label, focused):
    page, calls, status = undo_page
    status.update(status=initial, open_session=None,
                  allowed_actions=['START_OFFICE','START_REMOTE','MORNING_LEAVE','FULL_DAY_LEAVE'] if initial=='NOT_STARTED' else ['START_OFFICE','START_REMOTE'],
                  lunch_taken=initial=='LUNCH_BREAK', morning_leave=initial=='MORNING_LEAVE')
    page.locator('#refresh-status').click()
    expect(page.locator('#start-office')).to_be_enabled()

    def choose():
        if action == 'START_OFFICE':
            page.locator('#start-office').click()
        elif action == 'START_REMOTE':
            page.locator('#choose-remote').click()
            page.locator('#remote-reason').fill('Làm việc từ xa')
            page.locator('#remote-form button').click()
        else:
            page.locator('#choose-leave').click()
            page.locator('#morning-leave' if action=='MORNING_LEAVE' else '#full-day-leave').click()
            page.locator('#leave-reason').fill('Có việc gia đình')
            page.locator('#confirm-leave').click()

    choose()
    expect(page.locator('#undo-action')).to_be_visible()
    expect(page.locator('#undo-countdown')).to_contain_text(label + ':')
    expect(page.locator('#start-office')).to_be_disabled()
    expect(page.locator('#choose-remote')).to_be_disabled()
    expect(page.locator('#choose-leave')).to_be_disabled()
    page.clock.run_for(2000)
    assert calls == []
    page.get_by_role('button',name='Hoàn tác',exact=True).click()
    expect(page.locator('#'+focused)).to_be_focused()
    page.clock.run_for(6000)
    assert calls == []
    expect(page.locator('#start-office')).to_be_enabled()

    choose()
    page.clock.run_for(4999)
    assert calls == []
    page.clock.run_for(1)
    expect(page.locator('#message')).to_have_text('Đã ghi nhận thao tác.')
    page.clock.run_for(6000)
    assert len(calls) == 1
    assert calls[0]['action'] == action
    assert calls[0]['expected_revision'] == 1
    if action == 'START_OFFICE':
        assert calls[0]['latitude'] == 10.5 and calls[0]['longitude'] == 106.5
        assert page.evaluate('gpsCalls') == 2
        assert 'latitude' not in page.evaluate('JSON.stringify(sessionStorage)')
    else:
        assert page.evaluate('gpsCalls') == 0
        assert 'latitude' not in calls[0]
        assert calls[0]['reason'] == ('Làm việc từ xa' if action=='START_REMOTE' else 'Có việc gia đình')


def test_leaving_during_gps_lookup_does_not_start_delayed_checkin(undo_page):
    page, calls, status = undo_page
    status.update(status='NOT_STARTED',open_session=None,allowed_actions=['START_OFFICE','START_REMOTE'])
    page.locator('#refresh-status').click()
    expect(page.locator('#start-office')).to_be_enabled()
    page.evaluate('navigator.geolocation.getCurrentPosition = ok => { window.finishGps = ok; }')
    page.locator('#start-office').click()
    page.evaluate("location.hash = '#history'")
    expect(page.locator('#personal-history')).to_be_visible()
    page.evaluate('finishGps({coords:{latitude:10.5,longitude:106.5,accuracy:10}})')
    page.clock.run_for(6000)
    expect(page.locator('#undo-action')).to_be_hidden()
    assert calls == []
