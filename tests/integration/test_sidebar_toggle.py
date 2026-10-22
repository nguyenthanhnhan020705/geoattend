import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_office_browser import office_site
from tests.integration.test_admin_dashboard_browser import launch
from tests.pages_fixtures import pages_site, login_pages

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize('width', [360, 1280])
@pytest.mark.parametrize('role', ['worker', 'admin'])
def test_menu_collapses_after_selection_and_reopens(office_site, width, role):
    with sync_playwright() as p:
        browser, page = launch(p, width)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        login(page, office_site, role, 'Admin1234' if role == 'admin' else 'Worker1234')
        toggle = page.locator('#sidebar-toggle')
        if role == 'worker' and width <= 700:
            expect(toggle).to_be_hidden()
            page.get_by_role('link', name='Lịch sử cá nhân', exact=True).click()
            expect(page.locator('#history-form')).to_be_visible()
            expect(page.locator('.app-sidebar nav')).to_be_visible()
            page.get_by_role('link', name='Nộp báo cáo tuần', exact=True).click()
            expect(page.locator('.app-sidebar nav')).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert errors == []
            browser.close()
            return
        expect(toggle).to_have_attribute('aria-expanded', 'true')
        before = page.locator('main').bounding_box()['width']
        first = 'Xem trạng thái hôm nay' if role == 'admin' else 'Lịch sử cá nhân'
        page.get_by_role('link', name=first, exact=True).click()
        expect(toggle).to_have_attribute('aria-expanded', 'false')
        if width > 700:
            expect(page.locator('.app-sidebar nav')).to_be_visible()
            assert page.locator('.app-sidebar').bounding_box()['width'] == 88
        else:
            expect(page.locator('.app-sidebar nav')).to_be_hidden()
        assert page.locator('main').bounding_box()['width'] > before
        page.reload()
        expect(toggle).to_have_attribute('aria-expanded', 'false')
        toggle.click()
        expect(toggle).to_have_attribute('aria-expanded', 'true')
        expect(page.locator('nav a[aria-current="page"]')).to_have_text(first)
        second = 'Nhân viên báo cáo tuần' if role == 'admin' else 'Nộp báo cáo tuần'
        page.get_by_role('link', name=second, exact=True).click()
        expect(toggle).to_have_attribute('aria-expanded', 'false')
        toggle.focus()
        page.keyboard.press('Enter')
        expect(toggle).to_have_attribute('aria-expanded', 'true')
        expect(page.locator('nav a[aria-current="page"]')).to_have_text(second)
        page.keyboard.press('Escape')
        expect(toggle).to_have_attribute('aria-expanded', 'false')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert errors == []
        browser.close()


def test_pages_mobile_user_menu_stays_visible_between_functions(pages_site):
    site = pages_site
    page = site['browser'].new_page(viewport={'width':360,'height':900})
    login_pages(page, site)
    page.get_by_role('link', name='Nộp báo cáo tuần', exact=True).click()
    toggle = page.locator('#sidebar-toggle')
    expect(toggle).to_be_hidden()
    expect(page.locator('.app-sidebar nav')).to_be_visible()
    expect(page.locator('#report-week')).to_contain_text('19/10/2026')
    page.get_by_role('link', name='Đổi mật khẩu', exact=True).click()
    expect(page.locator('#password-form')).to_be_visible()
    expect(toggle).to_be_hidden()
    expect(page.locator('.app-sidebar nav')).to_be_visible()
    expect(page.locator('nav a[aria-current="page"]')).to_have_text('Đổi mật khẩu')
