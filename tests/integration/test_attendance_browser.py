from datetime import datetime,timezone
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright,expect
from tests.integration.test_browser import live_site,login
from tests.browser_attendance import open_remote,open_history,open_attendance

pytestmark=[pytest.mark.integration,pytest.mark.browser]


@pytest.fixture
def remote_site(live_site,migrated_db,monkeypatch):
    from app.accounts.service import create_user
    create_user(migrated_db,'worker','Nhân viên','Worker1234')
    migrated_db.commit()
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,2,tzinfo=timezone.utc))
    return live_site


def test_remote_browser_reload_history_and_retry(remote_site,migrated_db):
    artifacts=Path('.local-tests/phase-2/artifacts'); artifacts.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':360,'height':800})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.add_init_script("navigator.geolocation.getCurrentPosition=()=>{throw Error('GPS must not be requested')}")
        login(page,remote_site,'worker','Worker1234')
        expect(page.locator('#attendance-status')).to_contain_text('Chưa bắt đầu')
        reason='<img src=x onerror=alert(1)>'
        open_remote(page)
        page.get_by_label('Lý do làm Remote').fill(reason)
        # Server commits, but the browser loses its response. Retry must
        # reuse the UUID, even after status refresh shows WORKING_REMOTE.
        calls=[]
        def lose_response(route):
            calls.append(route.request.post_data_json)
            if len(calls)==1:
                route.fetch()
                route.abort('failed')
            else: route.continue_()
        page.route('**/api/attendance/actions',lose_response)
        page.get_by_role('button',name='Bắt đầu Remote',exact=True).click()
        expect(page.get_by_role('button',name='Gửi lại thao tác')).to_be_visible()
        page.get_by_role('button',name='Gửi lại thao tác').click()
        expect(page.locator('#attendance-status')).to_have_text('Đang làm Remote')
        assert calls[0]==calls[1]
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==1
        page.reload()
        expect(page.locator('#attendance-status')).to_have_text('Đang làm Remote')
        open_history(page)
        expect(page.locator('#history-list h3')).to_have_text('2026-10-14 · GHI NHẬN ĐÃ LÀM VIỆC REMOTE')
        expect(page.locator('#history-list li')).to_have_text(['09:00 · Check-in'])
        expect(page.locator('#history-list')).not_to_contain_text(reason)
        assert page.locator('#history-list img').count()==0
        open_attendance(page)
        page.locator('#check-out').click()
        page.get_by_label('Lý do Check-out sớm').fill('Có việc gia đình')
        page.locator('#checkout-form button').click()
        expect(page.locator('#attendance-status')).to_have_text('Đã Check-out',timeout=10000)
        expect(page.locator('#day-notice')).to_contain_text('ngày mai')
        expect(page.locator('#attendance-choices')).to_be_hidden()
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==1
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(artifacts/'remote-mobile.png'),full_page=True)
        open_history(page)
        page.get_by_label('Từ ngày').fill('2026-10-15')
        page.get_by_label('Đến ngày').fill('2026-10-14')
        page.get_by_role('button',name='Xem lịch sử').click()
        expect(page.locator('#history-message')).to_contain_text('Ngày bắt đầu')
        expect(page.locator('#history-list li')).to_have_text(['09:00 · Check-in','09:00 · Check-out'])
        assert errors==[]
        browser.close()
