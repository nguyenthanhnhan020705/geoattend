from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_office_browser import office_site
from tests.integration.test_admin_dashboard_browser import launch
from tests.pages_fixtures import pages_site, login_pages

pytestmark = [pytest.mark.integration, pytest.mark.browser]
LABELS = ['Chấm công', 'Lịch sử', 'Nộp báo cáo', 'Đổi mật khẩu', 'Đăng xuất']


def check_bottom_bar(page, width):
    bar = page.locator('.app-sidebar')
    expect(bar).to_be_visible()
    box = bar.bounding_box()
    assert box['x'] == 0 and box['width'] == width
    assert box['y'] + box['height'] == pytest.approx(page.viewport_size['height'], abs=1)
    expect(page.locator('#sidebar-toggle')).to_be_hidden()
    items = page.locator('.app-sidebar nav > a, .app-sidebar nav > button')
    expect(items).to_have_count(5)
    assert items.evaluate_all('(items)=>items.map(item=>item.dataset.mobileLabel)') == LABELS
    assert items.evaluate_all('(items)=>items.every(item=>{const img=item.querySelector(".mobile-nav-icon img");return img && img.complete && img.naturalWidth>0;})')
    expect(page.locator('.app-sidebar nav')).to_be_visible()
    assert page.locator('main').bounding_box()['x'] < 25
    assert page.locator('main').bounding_box()['width'] >= width - 25
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


@pytest.mark.parametrize('width', [320, 390, 430])
def test_mobile_user_bottom_bar_across_all_functions(office_site, width):
    with sync_playwright() as p:
        browser, page = launch(p, width)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        login(page, office_site, 'worker', 'Worker1234')
        check_bottom_bar(page, width)
        page.get_by_role('link', name='Lịch sử cá nhân', exact=True).click()
        expect(page.locator('#history-form')).to_be_visible()
        check_bottom_bar(page, width)
        page.get_by_role('link', name='Nộp báo cáo tuần', exact=True).click()
        expect(page.locator('#report-form')).to_be_visible()
        check_bottom_bar(page, width)
        page.get_by_role('link', name='Đổi mật khẩu', exact=True).click()
        expect(page.locator('#password-form')).to_be_visible()
        check_bottom_bar(page, width)
        expect(page.locator('nav a[aria-current="page"]')).to_have_attribute('data-mobile-label', 'Đổi mật khẩu')
        page.evaluate('scrollTo(0,document.documentElement.scrollHeight)')
        assert page.locator('#password-form button').bounding_box()['y'] + page.locator('#password-form button').bounding_box()['height'] <= page.locator('.app-sidebar').bounding_box()['y']
        artifacts = Path('.local-tests/mobile-bottom-navigation'); artifacts.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(artifacts / f'account-{width}.png'), full_page=True)
        page.get_by_role('link', name='Trang chủ chấm công', exact=True).click()
        expect(page.locator('.attendance-panel')).to_be_visible()
        check_bottom_bar(page, width)
        page.screenshot(path=str(artifacts / f'home-{width}.png'), full_page=True)
        page.reload()
        check_bottom_bar(page, width)
        page.get_by_role('button', name='Đăng xuất', exact=True).click()
        page.wait_for_url('**/login')
        assert errors == []
        browser.close()


def test_pages_bottom_bar_links_and_icons(pages_site):
    page = pages_site['browser'].new_page(viewport={'width':390, 'height':850})
    login_pages(page, pages_site)
    check_bottom_bar(page, 390)
    for image in page.locator('.mobile-nav-icon img').all():
        assert '/geoattend/static/images/navigation/' in image.get_attribute('src')
    page.get_by_role('link', name='Nộp báo cáo tuần', exact=True).click()
    expect(page.locator('#report-form')).to_be_visible()
    check_bottom_bar(page, 390)


def test_mobile_admin_keeps_sidebar(office_site):
    with sync_playwright() as p:
        browser, page = launch(p, 390)
        login(page, office_site, 'admin', 'Admin1234')
        expect(page.locator('#sidebar-toggle')).to_be_visible()
        assert page.locator('.app-sidebar').bounding_box()['width'] < 390
        expect(page.locator('nav a[aria-current="page"]')).to_have_text('Quản lý nhân viên')
        browser.close()
