import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_office_browser import office_site
from tests.integration.test_admin_dashboard_browser import launch

pytestmark=[pytest.mark.integration,pytest.mark.browser]


def dashboard_response(page,origin):
    response=page.request.get(origin+'/api/admin/dashboard')
    assert response.status==200
    return response.json()


def test_dashboard_refresh_clock_visibility_manual_and_no_gps(office_site):
    with sync_playwright() as p:
        browser,page=launch(p)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        login(page,office_site,'admin','Admin1234')
        data=dashboard_response(page,office_site);calls=[]
        page.clock.install()
        page.add_init_script("window.testVisibility='visible';Object.defineProperty(document,'visibilityState',{get:()=>window.testVisibility})")
        page.route('**/api/admin/dashboard',lambda route:(calls.append(1),route.fulfill(json=data)))
        page.goto(office_site+'/admin/dashboard')
        expect(page.locator('#total-users')).to_have_text('1')
        assert len(calls)==1
        page.clock.fast_forward(29999)
        assert len(calls)==1
        page.clock.fast_forward(1)
        expect(page.locator('#snapshot-time')).to_contain_text('09:00')
        expect(page.locator('#reload-dashboard')).to_have_attribute('aria-busy','false')
        assert len(calls)==2
        page.evaluate("window.testVisibility='hidden';document.dispatchEvent(new Event('visibilitychange'))")
        page.clock.fast_forward(90000)
        assert len(calls)==2
        page.evaluate("window.testVisibility='visible';document.dispatchEvent(new Event('visibilitychange'))")
        page.wait_for_timeout(50)
        assert len(calls)==3
        page.get_by_role('button',name='Tải lại dữ liệu',exact=True).click()
        page.wait_for_timeout(50)
        assert len(calls)==4
        expect(page.locator('#reload-dashboard')).to_have_attribute('aria-busy','false')
        page.clock.fast_forward(30000)
        expect(page.locator('#reload-dashboard')).to_have_attribute('aria-busy','false')
        assert len(calls)==5  # Visibility/manual reload did not leave duplicate timers.
        assert errors==[]
        browser.close()


def test_dashboard_ignores_old_response_and_recovers_stale_snapshot(office_site):
    from copy import deepcopy
    with sync_playwright() as p:
        browser,page=launch(p)
        login(page,office_site,'admin','Admin1234')
        old=dashboard_response(page,office_site)
        new=deepcopy(old);new['as_of']='2026-10-14T03:00:00Z';new['items'][0]['full_name']='Mới nhất'
        held=[];mode=['ok']
        def respond(route):
            if mode[0]=='hold':held.append(route)
            elif mode[0]=='503':route.fulfill(status=503,json={'code':'DATABASE_UNAVAILABLE','message':'Mạng lỗi'})
            else:route.fulfill(json=new if mode[0]=='new' else old)
        page.route('**/api/admin/dashboard',respond)
        page.clock.install()
        page.goto(office_site+'/admin/dashboard')
        expect(page.locator('#dashboard-users')).to_contain_text('Nhân viên')
        mode[0]='hold';page.locator('#reload-dashboard').click()
        page.wait_for_timeout(50)
        mode[0]='new';page.locator('#reload-dashboard').click()
        expect(page.locator('#dashboard-users')).to_contain_text('Mới nhất')
        held[0].fulfill(json=old)
        expect(page.locator('#dashboard-users')).to_contain_text('Mới nhất')
        expect(page.locator('#snapshot-time')).to_contain_text('10:00')
        mode[0]='503';page.locator('#reload-dashboard').click()
        expect(page.locator('#dashboard-message')).to_contain_text('Dữ liệu cũ')
        expect(page.locator('#dashboard-users')).to_contain_text('Mới nhất')
        mode[0]='hold';page.locator('#reload-dashboard').click()
        page.clock.fast_forward(15001)
        expect(page.locator('#dashboard-message')).to_contain_text('Dữ liệu cũ')
        mode[0]='new';page.locator('#reload-dashboard').click()
        expect(page.locator('#dashboard-message')).to_have_text('')
        browser.close()


@pytest.mark.parametrize('status',[401,403])
def test_dashboard_auth_failure_stops_polling(office_site,status):
    with sync_playwright() as p:
        browser,page=launch(p)
        login(page,office_site,'admin','Admin1234')
        data=dashboard_response(page,office_site);calls=[]
        def respond(route):
            calls.append(1)
            if len(calls)==1:route.fulfill(json=data)
            else:route.fulfill(status=status,json={'code':'AUTH_REQUIRED' if status==401 else 'FORBIDDEN','message':'Không có quyền'})
        page.route('**/api/admin/dashboard',respond)
        page.clock.install()
        page.goto(office_site+'/admin/dashboard')
        expect(page.locator('#total-users')).to_have_text('1')
        page.locator('#reload-dashboard').click()
        if status==401:expect(page).to_have_url(office_site+'/login')
        else:
            expect(page.locator('#dashboard-message')).to_contain_text('Không có quyền')
            expect(page.locator('#reload-dashboard')).to_be_disabled()
            page.clock.fast_forward(90000)
            assert len(calls)==2
        browser.close()


def test_dashboard_refresh_removes_marker_for_expired_gps_and_checkout(office_site):
    from copy import deepcopy
    from uuid import uuid4
    with sync_playwright() as p:
        browser,page=launch(p)
        login(page,office_site,'admin','Admin1234')
        data=dashboard_response(page,office_site)
        data['counts']['NOT_STARTED']=0;data['counts']['WORKING_OFFICE']=1
        item=data['items'][0];item['status']='WORKING_OFFICE'
        item['open_session']={'id':str(uuid4()),'work_mode':'OFFICE','start_time':data['as_of'],'start_reason':None}
        data['onsite']=[dict(**deepcopy(item),location_verified=True,location={'status':'available','expires_at':'2026-11-13T02:00:00Z','latitude':10.5,'longitude':106.5,'accuracy_m':15})]
        page.route('**/api/admin/dashboard',lambda route:route.fulfill(json=data))
        page.goto(office_site+'/admin/dashboard')
        expect(page.locator('.onsite-marker')).to_have_count(1)
        data['onsite'][0]['location']={'status':'expired','expires_at':data['as_of']}
        page.locator('#reload-dashboard').click()
        expect(page.locator('.onsite-marker')).to_have_count(0)
        expect(page.locator('#dashboard-users')).to_contain_text('Dữ liệu vị trí đã hết hạn lưu')
        data['onsite']=[];data['items'][0]['status']='CHECKED_OUT';data['items'][0]['open_session']=None
        data['counts']['WORKING_OFFICE']=0;data['counts']['CHECKED_OUT']=1
        page.locator('#reload-dashboard').click()
        expect(page.locator('[data-status="CHECKED_OUT"] .status-count')).to_have_text('1')
        expect(page.locator('.onsite-marker')).to_have_count(0)
        browser.close()

