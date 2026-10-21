from tests.browser_navigation import choose_menu, open_menu
import os
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_office_browser import office_site
from tests.integration.test_office import POLYGON

pytestmark=[pytest.mark.integration,pytest.mark.browser]


def launch(p,width=1280):
    channel=os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge')
    browser=p.chromium.launch(channel=None if channel=='chromium' else channel,headless=True)
    page=browser.new_page(viewport={'width':width,'height':900})
    page.set_default_timeout(5000)
    page.route('https://tiles.openfreemap.org/**',lambda route:route.abort())
    page.add_init_script("navigator.geolocation.getCurrentPosition=()=>{throw Error('Dashboard must never acquire GPS')};navigator.geolocation.watchPosition=()=>{throw Error('No tracking')}")
    return browser,page


@pytest.mark.parametrize('width',[360,1280])
def test_dashboard_map_history_navigation_and_xss(office_site,migrated_db,width):
    import json
    name='<img src=x onerror=alert(1)>'
    migrated_db.execute("UPDATE geoattend.profiles SET full_name=%s WHERE username='worker'",(name,))
    uid=migrated_db.execute("SELECT id FROM geoattend.profiles WHERE username='worker'").fetchone()['id']
    migrated_db.execute('INSERT INTO geoattend.office(name,address,geom,revision) VALUES(%s,%s,ST_GeomFromGeoJSON(%s),1)',('Office','HCM',json.dumps(POLYGON)))
    day=migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,'2026-10-14','WORKING_OFFICE') RETURNING id",(uid,)).fetchone()['id']
    session=migrated_db.execute("INSERT INTO geoattend.work_sessions(day_id,work_mode,start_time) VALUES(%s,'OFFICE','2026-10-14 02:00+00') RETURNING id",(day,)).fetchone()['id']
    event=migrated_db.execute("INSERT INTO geoattend.attendance_events(day_id,session_id,event_type,event_time,source,location_verified,reason) VALUES(%s,%s,'WORK_START','2026-10-14 02:00+00','USER',true,%s) RETURNING id",(day,session,name)).fetchone()['id']
    migrated_db.execute("INSERT INTO geoattend.office_locations(session_id,start_event_id,point,accuracy_m,recorded_at,expires_at) VALUES(%s,%s,ST_SetSRID(ST_MakePoint(106.5,10.5),4326),15,'2026-10-14 02:00+00','2026-11-13 02:00+00')",(session,event))
    migrated_db.commit()
    with sync_playwright() as p:
        browser,page=launch(p,width)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        login(page,office_site,'admin','Admin1234')
        choose_menu(page, 'Xem trạng thái hôm nay')
        expect(page.locator('#total-users')).to_have_text('1')
        expect(page.locator('[data-status="WORKING_OFFICE"] .status-count')).to_have_text('1')
        expect(page.locator('#dashboard-users li')).to_have_count(1)
        expect(page.locator('#dashboard-users')).to_contain_text(name)
        expect(page.locator('.onsite-marker')).to_have_count(1)
        expect(page.locator('#onsite-map .leaflet-interactive')).not_to_have_count(0)
        page.locator('.onsite-marker').click()
        popup=page.locator('.leaflet-popup-content')
        expect(popup).to_contain_text(name)
        expect(popup).to_contain_text('Đang làm tại văn phòng')
        expect(popup).to_contain_text('09:00')
        expect(popup).not_to_contain_text('GPS đã xác minh')
        expect(popup).not_to_contain_text('Sai số')
        popup.get_by_role('button',name='Lịch sử',exact=True).click()
        expect(page.locator('#employee-history-dialog')).to_contain_text(name)
        expect(page.locator('#employee-history-dialog')).not_to_contain_text('GPS đã xác minh')
        expect(page.locator('#employee-history-dialog')).not_to_contain_text('Sai số')
        assert page.locator('#dashboard-users img,.leaflet-popup-content img,#employee-history-dialog img').count()==0
        page.get_by_role('button',name='Đóng lịch sử',exact=True).click()
        expect(page.locator('#tile-message')).to_contain_text('Không tải được')
        page.get_by_role('button',name='Tải lại bản đồ',exact=True).click()
        expect(page.locator('#dashboard-users li')).to_have_count(1)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        artifacts=Path('.local-tests/phase-5/artifacts');artifacts.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(artifacts/f'dashboard-{width}.png'),full_page=True)
        choose_menu(page, 'Vùng văn phòng')
        expect(page.get_by_label('Tên văn phòng')).to_have_value('Office')
        choose_menu(page, 'Xem trạng thái hôm nay')
        choose_menu(page, 'Quản lý nhân viên')
        expect(page.locator('#users li')).to_have_count(1)
        assert errors==[]
        browser.close()


def test_dashboard_page_permissions(office_site):
    with sync_playwright() as p:
        browser,page=launch(p)
        page.goto(office_site+'/admin/dashboard')
        expect(page).to_have_url(office_site+'/login')
        login(page,office_site,'worker','Worker1234')
        response=page.goto(office_site+'/admin/dashboard')
        assert response.status==403
        browser.close()
