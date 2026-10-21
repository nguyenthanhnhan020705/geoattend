from tests.browser_navigation import choose_menu, open_menu
import os
import pytest
from playwright.sync_api import sync_playwright,expect
from tests.integration.test_office_browser import office_site
from tests.integration.test_browser import live_site,login

pytestmark=[pytest.mark.integration,pytest.mark.browser]


def test_office_request_timeout_releases_editor(office_site):
    with sync_playwright() as p:
        browser=p.chromium.launch(channel=os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge'),headless=True)
        page=browser.new_page();login(page,office_site,'admin','Admin1234')
        held=[]
        def hold(route):
            held.append(route)
            page.evaluate('()=>document.documentElement.dataset.officeWaiting="yes"')
        page.route('**/api/admin/office',hold)
        page.clock.install()
        page.goto(office_site+'/admin/office',wait_until='domcontentloaded')
        expect(page.locator('#office-form')).to_have_attribute('aria-busy','true')
        expect(page.locator('html')).to_have_attribute('data-office-waiting','yes')
        page.clock.fast_forward(20000)
        expect(page.locator('#office-form')).to_have_attribute('aria-busy','false',timeout=3000)
        expect(page.locator('#office-revision')).not_to_contain_text('Đang tải')
        expect(page.locator('#message')).to_contain_text('quá thời gian')
        expect(page.get_by_role('button',name='Tải lại bản đã lưu')).to_be_enabled()
        browser.close()


def test_map_click_draws_region_without_typing_coordinates(office_site,migrated_db):
    with sync_playwright() as p:
        browser=p.chromium.launch(channel=os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge'),headless=True)
        page=browser.new_page(viewport={'width':1280,'height':900})
        page.route('https://tiles.openfreemap.org/**',lambda route:route.fulfill(json={'version':8,'sources':{},'layers':[{'id':'land','type':'background','paint':{'background-color':'#dde6d5'}}]}))
        page.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
        login(page,office_site,'admin','Admin1234')
        choose_menu(page, 'Vùng văn phòng')
        expect(page.locator('#office-revision')).to_contain_text('0')
        expect(page.locator('#office-map')).to_have_attribute('data-map-state','ready')
        expect(page.locator('.leaflet-control-attribution')).to_contain_text('OpenFreeMap')
        expect(page.get_by_role('button',name='Vẽ vùng',exact=True)).to_be_visible()
        page.get_by_role('button',name='Vẽ vùng',exact=True).click()
        for x,y in [(150,130),(350,130),(350,300),(150,300)]:page.locator('#office-map').click(position={'x':x,'y':y})
        expect(page.locator('#vertices-list li')).to_have_count(4)
        page.locator('#retry-map').click()
        expect(page.locator('#office-map')).to_have_attribute('data-map-state','ready')
        expect(page.locator('.leaflet-control-attribution')).to_contain_text('OpenStreetMap')
        expect(page.locator('#vertices-list li')).to_have_count(4)
        page.get_by_label('Tên văn phòng').fill('Vùng vẽ trực tiếp')
        page.get_by_label('Địa chỉ',exact=True).fill('Kiểm thử')
        page.get_by_role('button',name='Xem trước').click()
        page.get_by_role('button',name='Lưu vùng văn phòng').click()
        expect(page.locator('#office-revision')).to_contain_text('1')
        assert migrated_db.execute('SELECT ST_NPoints(geom) AS n FROM geoattend.office').fetchone()['n']==5
        browser.close()
