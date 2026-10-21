from datetime import datetime,timezone
from pathlib import Path
import os
import pytest
from playwright.sync_api import sync_playwright,expect
from tests.integration.test_browser import live_site,login
from tests.integration.test_office import POLYGON
from tests.browser_attendance import open_history

pytestmark=[pytest.mark.integration,pytest.mark.browser]


@pytest.fixture
def office_site(live_site,migrated_db,monkeypatch):
    from app.accounts.service import create_user
    create_user(migrated_db,'worker','Nhân viên','Worker1234');migrated_db.commit()
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,2,tzinfo=timezone.utc))
    return live_site


def test_admin_map_and_user_gps_flow(office_site,migrated_db):
    artifacts=Path('.local-tests/phase-3/artifacts');artifacts.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        channel=os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge')
        browser=p.chromium.launch(channel=None if channel=='chromium' else channel,headless=True)
        admin=browser.new_page(viewport={'width':1280,'height':900})
        errors=[]; admin.on('pageerror',lambda error:errors.append(str(error)))
        admin.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
        admin.route('https://tiles.openfreemap.org/**',lambda route:route.abort())
        login(admin,office_site,'admin','Admin1234')
        admin.get_by_role('link',name='Văn phòng').click()
        expect(admin.locator('#office-revision')).to_contain_text('0')
        admin.get_by_label('Tên văn phòng').fill('Văn phòng kiểm thử')
        admin.get_by_label('Địa chỉ').fill('TP.HCM')
        for lat,lon in [(10,106),(10,107),(11,107),(11,106)]:
            admin.get_by_label('Vĩ độ mới').fill(str(lat));admin.get_by_label('Kinh độ mới').fill(str(lon))
            admin.get_by_role('button',name='Thêm đỉnh',exact=True).click()
        admin.get_by_role('button',name='Xem trước').click()
        expect(admin.locator('#office-map .leaflet-interactive')).not_to_have_count(0)
        admin.get_by_role('button',name='Lưu vùng văn phòng').click()
        expect(admin.locator('#office-revision')).to_contain_text('1')
        admin.reload()
        expect(admin.get_by_label('Tên văn phòng')).to_have_value('Văn phòng kiểm thử')
        expect(admin.locator('#vertices-list li')).to_have_count(4)
        admin.screenshot(path=str(artifacts/'office-admin-desktop.png'),full_page=True)
        context=browser.new_context(viewport={'width':360,'height':800})
        user=context.new_page();user.on('pageerror',lambda error:errors.append(str(error)))
        user.add_init_script("""window.gpsCalls=0; window.gpsMode='inside'; navigator.geolocation.getCurrentPosition=(ok,fail)=>{window.gpsCalls++;if(window.gpsMode==='denied')return fail({code:1});ok({coords:{latitude:window.gpsMode==='outside'?12:10.5,longitude:106.5,accuracy:50000}})};navigator.geolocation.watchPosition=()=>{throw Error('Continuous GPS forbidden')};""")
        login(user,office_site,'worker','Worker1234')
        user.get_by_role('button',name='CHECK-IN OFFICE',exact=True).click()
        expect(user.locator('#attendance-status')).to_have_text('Đang làm tại văn phòng')
        assert user.evaluate('gpsCalls')==1
        assert user.evaluate('sessionStorage.getItem("geoattend.pendingAttendance")') is None
        user.reload()
        expect(user.locator('#attendance-status')).to_have_text('Đang làm tại văn phòng')
        open_history(user)
        expect(user.locator('#history-list h3')).to_have_text('2026-10-14 · GHI NHẬN ĐÃ LÀM VIỆC OFFICE')
        expect(user.locator('#history-list li')).to_have_text(['09:00 · Check-in'])
        expect(user.locator('#history-list')).to_contain_text('Đang làm việc')
        expect(user.locator('#history-list')).not_to_contain_text('GPS')
        expect(user.locator('#history-list')).not_to_contain_text('50000')
        user.locator('#start-lunch').click()
        expect(user.locator('#attendance-status')).to_have_text('Đang nghỉ trưa')
        assert user.evaluate('gpsCalls')==0
        user.evaluate("window.gpsMode='denied'")
        user.get_by_role('button',name='TIẾP TỤC OFFICE',exact=True).click()
        expect(user.locator('#message')).to_contain_text('quyền vị trí')
        expect(user.locator('#attendance-status')).to_have_text('Đang nghỉ trưa')
        expect(user.get_by_role('button',name='TIẾP TỤC REMOTE',exact=True)).to_be_enabled()
        user.evaluate("window.gpsMode='outside'")
        user.get_by_role('button',name='TIẾP TỤC OFFICE',exact=True).click()
        expect(user.locator('#message')).to_contain_text('ngoài vùng')
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==1
        user.evaluate("window.gpsMode='inside'")
        user.get_by_role('button',name='TIẾP TỤC OFFICE',exact=True).click()
        expect(user.locator('#attendance-status')).to_have_text('Đang làm tại văn phòng')
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==2
        assert user.evaluate('document.documentElement.scrollWidth<=innerWidth')
        user.screenshot(path=str(artifacts/'office-user-mobile.png'),full_page=True)
        # Stale Admin draft stays present until explicit reload.
        admin.get_by_label('Tên văn phòng').fill('Bản nháp đang sửa')
        migrated_db.execute('UPDATE geoattend.office SET revision=revision+1');migrated_db.commit()
        admin.get_by_role('button',name='Xem trước').click()
        admin.get_by_role('button',name='Lưu vùng văn phòng').click()
        expect(admin.locator('#message')).to_contain_text('thay đổi')
        expect(admin.get_by_label('Tên văn phòng')).to_have_value('Bản nháp đang sửa')
        admin.set_viewport_size({'width':360,'height':800})
        assert admin.evaluate('document.documentElement.scrollWidth<=innerWidth')
        admin.screenshot(path=str(artifacts/'office-admin-mobile.png'),full_page=True)
        assert errors==[]
        browser.close()


def test_office_ambiguous_retry_no_persistent_gps(office_site,migrated_db):
    import json
    migrated_db.execute('INSERT INTO geoattend.office(name,address,geom,revision) VALUES(%s,%s,ST_GeomFromGeoJSON(%s),1)',('Office','HCM',json.dumps(POLYGON)));migrated_db.commit()
    with sync_playwright() as p:
        channel=os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge')
        browser=p.chromium.launch(channel=None if channel=='chromium' else channel,headless=True)
        page=browser.new_page()
        page.add_init_script("window.gpsCalls=0;navigator.geolocation.getCurrentPosition=ok=>{window.gpsCalls++;ok({coords:{latitude:10.5,longitude:106.5,accuracy:12}})}")
        login(page,office_site,'worker','Worker1234')
        calls=[]
        def lose_first(route):
            calls.append(route.request.post_data_json)
            if len(calls)==1: route.fetch();route.abort('failed')
            else:route.continue_()
        page.route('**/api/attendance/actions',lose_first)
        page.get_by_role('button',name='CHECK-IN OFFICE',exact=True).click()
        expect(page.get_by_role('button',name='Gửi lại thao tác')).to_be_visible()
        assert page.evaluate('sessionStorage.getItem("geoattend.pendingAttendance")') is None
        assert page.evaluate('JSON.stringify(localStorage)')=='{}'
        page.get_by_role('button',name='Gửi lại thao tác').click()
        expect(page.locator('#attendance-status')).to_have_text('Đang làm tại văn phòng')
        assert calls[0]==calls[1] and page.evaluate('gpsCalls')==1
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==1
        browser.close()


def test_office_loading_blocks_edits_until_response(office_site):
    with sync_playwright() as p:
        channel=os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge')
        browser=p.chromium.launch(channel=None if channel=='chromium' else channel,headless=True)
        page=browser.new_page()
        page.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
        page.route('https://tiles.openfreemap.org/**',lambda route:route.abort())
        login(page,office_site,'admin','Admin1234')
        held=[];get_count=[0]
        def delay_get(route):
            if route.request.method=='GET':
                held.append((route,route.fetch()));get_count[0]+=1
                page.evaluate('count=>document.documentElement.dataset.heldGets=String(count)',get_count[0])
            else:route.continue_()
        page.route('**/api/admin/office',delay_get)
        page.goto(office_site+'/admin/office',wait_until='domcontentloaded')
        expect(page.locator('html')).to_have_attribute('data-held-gets','1')
        expect(page.get_by_label('Tên văn phòng')).to_be_disabled()
        expect(page.get_by_role('button',name='Thêm đỉnh',exact=True)).to_be_disabled()
        expect(page.locator('#office-form')).to_have_attribute('aria-busy','true')
        assert len(held)==1
        route,response=held.pop();route.fulfill(response=response)
        expect(page.get_by_label('Tên văn phòng')).to_be_enabled()
        page.get_by_label('Tên văn phòng').fill('Bản nháp sẽ được bỏ theo xác nhận')
        page.on('dialog',lambda dialog:dialog.accept())
        page.get_by_role('button',name='Tải lại bản đã lưu').click()
        expect(page.locator('html')).to_have_attribute('data-held-gets','2')
        expect(page.get_by_label('Tên văn phòng')).to_be_disabled()
        expect(page.get_by_role('button',name='Tải lại bản đã lưu')).to_be_disabled()
        page.locator('#office-map').click(position={'x':100,'y':100})
        expect(page.locator('#vertices-list li')).to_have_count(0)
        assert len(held)==1
        route,response=held.pop();route.fulfill(response=response)
        expect(page.get_by_label('Tên văn phòng')).to_be_enabled()
        expect(page.get_by_role('button',name='Tải lại bản đã lưu')).to_be_enabled()
        # A failed reload also releases controls and preserves the draft.
        page.get_by_label('Tên văn phòng').fill('Giữ khi tải lỗi')
        page.get_by_role('button',name='Tải lại bản đã lưu').click()
        expect(page.locator('html')).to_have_attribute('data-held-gets','3')
        expect(page.get_by_label('Tên văn phòng')).to_be_disabled()
        route,_=held.pop();route.fulfill(status=503,json={'code':'DATABASE_UNAVAILABLE','message':'Chưa sẵn sàng'})
        expect(page.get_by_label('Tên văn phòng')).to_be_enabled()
        expect(page.get_by_label('Tên văn phòng')).to_have_value('Giữ khi tải lỗi')
        browser.close()
