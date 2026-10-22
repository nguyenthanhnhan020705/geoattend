import pytest
from pathlib import Path
from playwright.sync_api import expect
from tests.test_mobile_navigation_preview import preview


@pytest.mark.parametrize('width,pages', [(320,False),(390,False),(430,True)])
def test_admin_six_items_fixed_at_bottom(preview, width, pages):
    page, _ = preview(width,role='ADMIN',pages=pages,path='/account')
    nav = page.locator('.app-sidebar')
    expect(nav.locator('nav>a')).to_have_count(5)
    expect(nav.locator('#logout')).to_be_visible()
    expect(page.locator('#sidebar-toggle')).not_to_be_visible()
    box=nav.bounding_box()
    assert box['x']==0 and box['width']==width
    assert abs(box['y']+box['height']-850)<2
    assert page.locator('.workspace').bounding_box()['x']==0
    for item in nav.locator('nav>a,nav>button').all():
        rect=item.bounding_box()
        assert rect['width']>=44 and rect['height']>=44
        expect(item.locator('svg')).to_be_visible()
        assert item.get_attribute('data-mobile-label')
    expect(nav.get_by_role('link',name='Tài khoản cá nhân',exact=True)).to_have_attribute('aria-current','page')
    page.evaluate('scrollTo(0,document.documentElement.scrollHeight)')
    assert nav.bounding_box()==box
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.locator('body').evaluate("el=>el.classList.add('sidebar-collapsed')")
    expect(nav.locator('nav')).to_be_visible()
    assert nav.bounding_box()==box
    folder=Path('.local-tests/admin-bottom-preview');folder.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(folder/f'admin-{width}.png'),full_page=True)
