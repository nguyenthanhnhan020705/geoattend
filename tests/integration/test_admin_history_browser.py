import os
from uuid import uuid4
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_office_browser import office_site
from tests.browser_attendance import open_remote

pytestmark = [pytest.mark.integration,pytest.mark.browser]


@pytest.mark.parametrize('width',[360,1280])
def test_admin_history_confirm_delete_retry_and_user_visibility(office_site,migrated_db,width):
    with sync_playwright() as p:
        channel = os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge')
        browser = p.chromium.launch(channel=None if channel=='chromium' else channel,headless=True)
        page = browser.new_page(viewport={'width':width,'height':900})
        page.set_default_timeout(5000)
        errors=[]; page.on('pageerror',lambda error:errors.append(str(error)))
        login(page,office_site,'worker','Worker1234')
        reason='<img src=x onerror=alert(1)>'
        open_remote(page)
        page.get_by_label('Lý do làm Remote').fill(reason)
        page.get_by_role('button',name='Bắt đầu Remote',exact=True).click()
        expect(page.locator('#attendance-status')).to_have_text('Đang làm Remote')
        page.get_by_role('button',name='Đăng xuất',exact=True).click()
        page.wait_for_url('**/login')
        login(page,office_site,'admin','Admin1234')
        page.get_by_role('button',name='Lịch sử',exact=True).click()
        history=page.locator('#employee-history-dialog')
        expect(history).to_be_visible()
        expect(history).to_contain_text(reason)
        assert history.locator('img').count()==0
        expect(history.get_by_role('button',name='Xóa ngày này',exact=True)).to_be_disabled()
        page.get_by_role('button',name='Đóng lịch sử',exact=True).click()
        page.get_by_role('button',name='Đăng xuất',exact=True).click()
        page.wait_for_url('**/login')
        login(page,office_site,'worker','Worker1234')
        page.locator('#check-out').click()
        page.get_by_label('Lý do Check-out sớm').fill('Có việc gia đình')
        page.locator('#checkout-form button').click()
        expect(page.locator('#attendance-status')).to_have_text('Đã Check-out')
        page.get_by_role('button',name='Đăng xuất',exact=True).click()
        page.wait_for_url('**/login')
        login(page,office_site,'admin','Admin1234')
        page.get_by_role('button',name='Lịch sử',exact=True).click()
        expect(history).to_contain_text('Đã Check-out')
        history.get_by_role('button',name='Xóa ngày này',exact=True).click()
        confirmation=page.locator('#delete-history-dialog')
        expect(confirmation).to_contain_text('Không thể khôi phục')
        page.get_by_label('Nhập tên tài khoản để xác nhận').fill('sai')
        expect(confirmation.get_by_role('button',name='Xóa vĩnh viễn',exact=True)).to_be_disabled()
        page.get_by_label('Nhập tên tài khoản để xác nhận').fill('worker')
        calls=[]
        def lose_first(route):
            if route.request.method=='DELETE':
                calls.append(route.request.post_data_json)
                if len(calls)==1:
                    route.fetch(); route.abort('failed')
                else: route.continue_()
            else: route.continue_()
        page.route('**/api/admin/users/*/history/*',lose_first)
        confirmation.get_by_role('button',name='Xóa vĩnh viễn',exact=True).click()
        expect(page.locator('#delete-history-message')).to_contain_text('Không thể kết nối')
        confirmation.get_by_role('button',name='Xóa vĩnh viễn',exact=True).click()
        expect(confirmation).not_to_be_visible()
        expect(history).to_contain_text('Chưa có lịch sử')
        assert calls[0]==calls[1]
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.get_by_role('button',name='Đóng lịch sử',exact=True).click()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==0
        assert errors==[]
        browser.close()
