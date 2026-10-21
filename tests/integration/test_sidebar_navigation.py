from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_office_browser import office_site
from tests.integration.test_admin_dashboard_browser import launch
from tests.pages_fixtures import pages_site, login_pages

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize('path, module, active', [
    ('/user/weekly-reports', 'user-weekly-reports.js', 'Nộp báo cáo tuần'),
    ('/account', 'account.js', 'Đổi mật khẩu'),
])
def test_user_menu_is_present_before_page_module_loads(office_site, path, module, active):
    with sync_playwright() as p:
        browser, page = launch(p, 1280)
        login(page, office_site, 'worker', 'Worker1234')
        page.route('**/static/js/' + module + '*', lambda route: route.abort())
        page.goto(office_site + path)
        nav = page.get_by_role('navigation', name='Điều hướng')
        expect(nav.get_by_role('link')).to_have_text([
            'Trang chủ chấm công', 'Lịch sử cá nhân', 'Nộp báo cáo tuần', 'Đổi mật khẩu'])
        expect(nav.locator('[aria-current="page"]')).to_have_text(active)
        browser.close()


@pytest.mark.parametrize('width', [360, 1280])
def test_user_sidebar_history_and_account(office_site, width):
    with sync_playwright() as p:
        browser, page = launch(p, width)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        login(page, office_site, 'worker', 'Worker1234')
        nav = page.get_by_role('navigation', name='Điều hướng')
        expect(nav.get_by_role('link')).to_have_text([
            'Trang chủ chấm công', 'Lịch sử cá nhân', 'Nộp báo cáo tuần', 'Đổi mật khẩu'])
        expect(page.locator('.attendance-panel')).to_be_visible()
        expect(page.locator('#personal-history')).to_be_hidden()
        nav.get_by_role('link', name='Lịch sử cá nhân', exact=True).click()
        expect(page.locator('#personal-history')).to_be_visible()
        expect(page.locator('#history-form')).to_be_visible()
        expect(page.locator('.attendance-panel')).to_be_hidden()
        expect(page.locator('#history-page')).to_contain_text('/')
        page.reload()
        expect(page.locator('#history-form')).to_be_visible()
        page.go_back()
        expect(page.locator('.attendance-panel')).to_be_visible()
        nav.get_by_role('link', name='Đổi mật khẩu', exact=True).click()
        expect(page.locator('#password-form')).to_be_visible()
        expect(page.locator('nav a[aria-current="page"]')).to_have_text('Đổi mật khẩu')
        assert page.locator('.app-sidebar').bounding_box()['x'] < page.locator('main').bounding_box()['x']
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert errors == []
        browser.close()


def test_pages_history_sidebar_routes_and_logout(pages_site):
    site = pages_site
    page = site['browser'].new_page(viewport={'width':360, 'height':900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    login_pages(page, site)
    history = page.get_by_role('link', name='Lịch sử cá nhân', exact=True)
    expect(history).to_have_attribute('href', '/geoattend/user/#history')
    history.click()
    expect(page.locator('#history-page')).to_contain_text('/')
    expect(history).to_have_attribute('aria-current', 'page')
    page.get_by_role('link', name='Nộp báo cáo tuần', exact=True).click()
    expect(page.locator('#report-week')).to_contain_text('19/10/2026')
    page.get_by_role('link', name='Lịch sử cá nhân', exact=True).click()
    expect(page.locator('#history-form')).to_be_visible()
    expect(page.locator('#history-page')).to_contain_text('/')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_role('button', name='Đăng xuất', exact=True).click()
    page.wait_for_url('**/login/')
    assert errors == []


@pytest.mark.parametrize('width', [360, 1280])
def test_admin_sidebar_and_export_location(office_site, width):
    with sync_playwright() as p:
        browser, page = launch(p, width)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        login(page, office_site, 'admin', 'Admin1234')
        nav = page.get_by_role('navigation', name='Điều hướng')
        expect(nav.get_by_role('link')).to_have_text([
            'Xem trạng thái hôm nay', 'Nhân viên báo cáo tuần', 'Quản lý nhân viên',
            'Vùng văn phòng', 'Tài khoản cá nhân'])
        expect(page.locator('#export-attendance')).to_be_enabled()
        nav.get_by_role('link', name='Xem trạng thái hôm nay', exact=True).click()
        expect(page.locator('#dashboard-users li')).to_have_count(1)
        expect(page.locator('#attendance-export-form')).to_have_count(0)
        nav.get_by_role('link', name='Nhân viên báo cáo tuần', exact=True).click()
        expect(page.locator('nav a[aria-current="page"]')).to_have_text('Nhân viên báo cáo tuần')
        nav.get_by_role('link', name='Tài khoản cá nhân', exact=True).click()
        expect(page.locator('#password-form')).to_be_visible()
        expect(page.locator('nav a[aria-current="page"]')).to_have_text('Tài khoản cá nhân')
        assert page.locator('.app-sidebar').bounding_box()['x'] < page.locator('main').bounding_box()['x']
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        artifacts = Path('.local-tests/sidebar'); artifacts.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(artifacts / f'admin-account-{width}.png'), full_page=True)
        assert errors == []
        browser.close()
