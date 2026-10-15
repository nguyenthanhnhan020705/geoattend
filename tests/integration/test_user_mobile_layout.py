import os
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_office_browser import office_site

pytestmark = [pytest.mark.integration,pytest.mark.browser]


@pytest.mark.parametrize('width',[360,1280])
def test_account_first_reason_panels_and_lazy_history(office_site,migrated_db,width):
    with sync_playwright() as p:
        channel=os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge')
        browser=p.chromium.launch(channel=None if channel=='chromium' else channel,headless=True)
        page=browser.new_page(viewport={'width':width,'height':800})
        page.set_default_timeout(5000)
        errors=[]; history_calls=[]; actions=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        def record(request):
            if '/api/attendance/history' in request.url: history_calls.append(request.url)
            if '/api/attendance/actions' in request.url: actions.append(request.post_data_json)
        page.on('request',record)
        page.add_init_script("navigator.geolocation.getCurrentPosition=()=>{throw Error('No GPS on Remote/leave/panel open')}")
        login(page,office_site,'worker','Worker1234')
        expect(page.locator('#attendance-status')).to_have_text('Chưa bắt đầu')
        expect(page.get_by_role('button',name='CHECK-IN OFFICE',exact=True)).to_be_enabled()
        expect(page.get_by_role('button',name='CHECK-IN REMOTE',exact=True)).to_be_enabled()
        expect(page.get_by_role('button',name='XIN NGHỈ',exact=True)).to_be_enabled()
        expect(page.get_by_label('Lý do làm Remote')).to_be_hidden()
        expect(page.get_by_label('Lý do nghỉ')).to_be_hidden()
        expect(page.locator('#history-form')).to_be_hidden()
        assert page.evaluate("document.querySelector('main').firstElementChild.id")=='employee-account'
        assert page.evaluate("document.querySelector('main').lastElementChild.id")=='personal-history'
        assert history_calls==[] and actions==[]
        page.get_by_role('button',name='CHECK-IN REMOTE',exact=True).click()
        expect(page.get_by_label('Lý do làm Remote')).to_be_focused()
        page.get_by_label('Lý do làm Remote').fill('Bản nháp Remote')
        page.get_by_role('button',name='XIN NGHỈ',exact=True).click()
        expect(page.get_by_label('Lý do nghỉ')).to_be_focused()
        expect(page.get_by_label('Lý do làm Remote')).to_be_hidden()
        page.get_by_role('button',name='Đóng nhập lý do',exact=True).click()
        expect(page.get_by_label('Lý do nghỉ')).to_be_hidden()
        assert actions==[]
        page.get_by_role('button',name='CHECK-IN REMOTE',exact=True).click()
        expect(page.get_by_label('Lý do làm Remote')).to_have_value('Bản nháp Remote')
        page.get_by_role('button',name='Bắt đầu Remote',exact=True).click()
        expect(page.locator('#attendance-status')).to_have_text('Đang làm Remote')
        expect(page.get_by_label('Lý do làm Remote')).to_be_hidden()
        assert history_calls==[] and len(actions)==1
        page.locator('#personal-history > summary').click()
        expect(page.locator('#history-list')).to_contain_text('Bản nháp Remote')
        assert len(history_calls)==1
        page.locator('#personal-history > summary').click()
        expect(page.locator('#history-form')).to_be_hidden()
        page.locator('#check-out').click()
        expect(page.locator('#attendance-status')).to_have_text('Đã Check-out')
        assert len(history_calls)==1
        page.locator('#personal-history > summary').click()
        expect(page.locator('#history-list')).to_contain_text('Đã Check-out')
        assert len(history_calls)==2
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('#personal-history > summary').click()
        artifacts=Path('.local-tests/user-mobile/artifacts');artifacts.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(artifacts/f'user-{width}.png'),full_page=True)
        assert errors==[]
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==1
        browser.close()


def test_reopening_history_ignores_older_inflight_response(office_site):
    with sync_playwright() as p:
        channel=os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge')
        browser=p.chromium.launch(channel=None if channel=='chromium' else channel,headless=True)
        page=browser.new_page(viewport={'width':360,'height':800})
        page.set_default_timeout(5000)
        login(page,office_site,'worker','Worker1234')
        expect(page.locator('#attendance-status')).to_have_text('Chưa bắt đầu')
        held=[]
        def delay_first(route):
            if not held:
                held.append((route,route.fetch()))
                page.evaluate("document.documentElement.dataset.historyHeld='yes'")
            else:route.continue_()
        page.route('**/api/attendance/history?*',delay_first)
        page.locator('#personal-history > summary').click()
        expect(page.locator('html')).to_have_attribute('data-history-held','yes')
        page.locator('#personal-history > summary').click()
        page.get_by_role('button',name='CHECK-IN REMOTE',exact=True).click()
        page.get_by_label('Lý do làm Remote').fill('Phiên mới sau phản hồi cũ')
        page.get_by_role('button',name='Bắt đầu Remote',exact=True).click()
        expect(page.locator('#attendance-status')).to_have_text('Đang làm Remote')
        page.locator('#personal-history > summary').click()
        expect(page.locator('#history-list')).to_contain_text('Phiên mới sau phản hồi cũ')
        route,response=held[0];route.fulfill(response=response)
        # All transport responses have settled before checking the rendered result.
        page.wait_for_load_state('networkidle')
        expect(page.locator('#history-list')).to_contain_text('Phiên mới sau phản hồi cũ')
        browser.close()
