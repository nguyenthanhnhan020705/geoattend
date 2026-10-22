from pathlib import Path

import pytest
from playwright.sync_api import expect
from tests.test_mobile_navigation_preview import preview


@pytest.mark.parametrize('width', [1024, 1440])
@pytest.mark.parametrize('role', ['USER', 'ADMIN'])
def test_desktop_compact_icon_rail_and_fixed_toggle(preview, width, role):
    page, _ = preview(width=width, role=role, path='/account' if role == 'ADMIN' else '/user')
    sidebar = page.locator('.app-sidebar')
    toggle = page.locator('#sidebar-toggle')
    expect(toggle).to_be_visible()
    initial = toggle.bounding_box()
    assert sidebar.bounding_box()['width'] == 248
    icons = page.locator('.app-sidebar nav .mobile-nav-icon, .app-sidebar nav .navigation-icon')
    expect(icons).to_have_count(6 if role == 'ADMIN' else 5)
    assert all(icon.is_visible() for icon in icons.all())
    assert page.locator('main').bounding_box()['y'] >= 80
    artifacts = Path('.local-tests/desktop-rail-preview'); artifacts.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(artifacts / f'{role}-expanded-{width}.png'), animations='disabled')
    toggle.click()
    expect(toggle).to_have_attribute('aria-expanded', 'false')
    expect(page.locator('.app-sidebar nav')).to_be_visible()
    assert sidebar.bounding_box()['width'] == 88
    assert toggle.bounding_box() == initial
    expect(page.locator('.app-sidebar .brand')).to_be_visible()
    assert all(icon.is_visible() for icon in icons.all())
    for text in page.locator('.app-sidebar nav .nav-label').all():
        expect(text).to_be_hidden()
    label = 'Tài khoản cá nhân' if role == 'ADMIN' else 'Nộp báo cáo tuần'
    page.get_by_role('link', name=label, exact=True).click()
    expect(toggle).to_have_attribute('aria-expanded', 'false')
    expect(page.locator('nav a[aria-current="page"]')).to_have_attribute('aria-label', label)
    expect(page.locator('.app-sidebar nav')).to_be_visible()
    assert toggle.bounding_box() == initial
    page.screenshot(path=str(artifacts / f'{role}-compact-{width}.png'), animations='disabled')
    page.locator('main').evaluate("el=>el.style.minHeight='1800px'")
    page.evaluate('scrollTo(0,500)')
    assert toggle.bounding_box() == initial
    toggle.focus()
    page.keyboard.press('Enter')
    expect(toggle).to_have_attribute('aria-expanded', 'true')
    assert toggle.bounding_box() == initial
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
