import json

import pytest
from playwright.sync_api import expect
from tests.pages_fixtures import pages_site, login_pages

pytestmark = [pytest.mark.integration, pytest.mark.browser]


def test_unconfigured_api_disables_login(pages_site):
    site = pages_site
    config = site['public'] / 'static/js/runtime-config.js'
    config.write_text('export const runtimeConfig = '+json.dumps(dict(mode='pages',basePath='/geoattend/',apiOrigin='',version='offline'))+';',encoding='utf-8')
    page = site['browser'].new_page()
    posts = []
    page.on('request', lambda request: posts.append(request.url) if request.method=='POST' else None)
    page.goto(site['url']+'/')
    expect(page.get_by_role('button',name='Đăng nhập',exact=True)).to_be_disabled()
    expect(page.locator('#message')).to_contain_text('chưa được kết nối')
    assert not posts


@pytest.mark.parametrize('width',[360,1280])
def test_bearer_login_reload_role_and_deep_links(pages_site,width):
    site = pages_site
    context = site['browser'].new_context(viewport={'width':width,'height':900})
    page = context.new_page()
    errors, failed = [], []
    page.on('pageerror',lambda error: errors.append(str(error)))
    page.on('response',lambda response: failed.append(response.url) if response.status==404 else None)
    login_pages(page,site)
    expect(page.locator('#full-name')).to_have_text('Nhân viên Pages')
    page.reload()
    expect(page.locator('#full-name')).to_have_text('Nhân viên Pages')
    assert not context.cookies(site['api'])
    page.goto(site['url']+'/admin/users/')
    page.wait_for_url('**/user/')
    expect(page.locator('#full-name')).to_have_text('Nhân viên Pages')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors and not failed
    page.get_by_role('button',name='Đăng xuất',exact=True).click()
    page.wait_for_url('**/login/')
    page.goto(site['url']+'/user/')
    page.wait_for_url('**/login/')


def test_no_api_calls_before_guard_and_storage_failure(pages_site):
    site=pages_site
    page=site['browser'].new_page()
    requested=[]
    page.on('request',lambda request:requested.append(request.url) if request.url.startswith(site['api']) else None)
    page.goto(site['url']+'/admin/dashboard/')
    page.wait_for_url('**/login/')
    assert not requested
    page.add_init_script("Object.defineProperty(window,'sessionStorage',{get(){throw new Error('blocked')}})")
    page.reload()
    expect(page.get_by_role('button',name='Đăng nhập',exact=True)).to_be_disabled()
    expect(page.locator('#message')).to_contain_text('lưu phiên')
    assert not requested


def test_transport_rejects_external_paths_and_network_keeps_token(pages_site):
    site=pages_site
    page=site['browser'].new_page()
    login_pages(page,site)
    result=page.evaluate("""async () => {
        const t=await import('/geoattend/static/js/transport.js');
        let rejected=0;
        for(const value of ['https://evil.test/api/x','//evil.test/api/x','/api/../x','/api/a\\\\b']) {
            try { t.apiUrl(value); } catch { rejected++; }
        }
        return rejected;
    }""")
    assert result==4
    saved=page.evaluate('JSON.stringify(sessionStorage)')
    page.route(site['api']+'/**',lambda route:route.abort())
    page.reload()
    expect(page.locator('#message')).to_contain_text('kết nối')
    assert page.evaluate('JSON.stringify(sessionStorage)')==saved


def test_expired_session_on_active_page_redirects_without_sending_request(pages_site):
    site=pages_site
    page=site['browser'].new_page()
    login_pages(page,site)
    expect(page.locator('#attendance-status')).to_contain_text('Chưa bắt đầu')
    page.evaluate("""() => {
        for(const key of Object.keys(sessionStorage)) {
            if(key.endsWith(':session')) {
                const value=JSON.parse(sessionStorage.getItem(key));
                value.expiresAt='2000-01-01T00:00:00Z';
                sessionStorage.setItem(key,JSON.stringify(value));
            }
        }
        document.getElementById('refresh-status').click();
    }""")
    page.wait_for_url('**/login/',timeout=5000)


@pytest.mark.parametrize('width',[360,1280])
def test_office_geofence_and_ambiguous_retry_then_remote(pages_site,migrated_db,width):
    site=pages_site
    admin=site['browser'].new_page(viewport={'width':width,'height':900})
    errors=[]
    admin.on('pageerror',lambda error:errors.append(str(error)))
    login_pages(admin,site,'admin','Admin1234')
    admin.get_by_role('link',name='Văn phòng',exact=True).click()
    expect(admin.locator('#office-name')).to_be_enabled()
    admin.get_by_label('Tên văn phòng').fill('Pages Office')
    admin.get_by_label('Địa chỉ',exact=True).fill('HCM')
    for lat,lon in [(10,106),(10,107),(11,107),(11,106)]:
        admin.get_by_label('Vĩ độ mới').fill(str(lat))
        admin.get_by_label('Kinh độ mới').fill(str(lon))
        admin.get_by_role('button',name='Thêm đỉnh',exact=True).click()
    admin.get_by_role('button',name='Xem trước',exact=True).click()
    admin.get_by_role('button',name='Lưu vùng văn phòng',exact=True).click()
    expect(admin.locator('#message')).to_contain_text('Đã lưu')
    user=site['browser'].new_page(viewport={'width':width,'height':900})
    user.on('pageerror',lambda error:errors.append(str(error)))
    user.add_init_script("navigator.geolocation.getCurrentPosition=ok=>ok({coords:{latitude:10.5,longitude:106.5,accuracy:12}})")
    login_pages(user,site)
    calls=[]
    def lose_first(route):
        if route.request.method=='OPTIONS':
            route.continue_();return
        calls.append(route.request.post_data_json)
        if len(calls)==1:
            route.fetch();route.abort('failed')
        else:
            route.continue_()
    user.route(site['api']+'/api/attendance/actions',lose_first)
    user.get_by_role('button',name='CHECK-IN OFFICE',exact=True).click()
    expect(user.locator('#retry-action')).to_be_visible()
    assert 'latitude' not in user.evaluate('JSON.stringify(sessionStorage)')
    user.locator('#retry-action').click()
    expect(user.locator('#attendance-status')).to_have_text('Đang làm tại văn phòng')
    assert calls[0]==calls[1]
    user.get_by_role('button',name='NGHỈ TRƯA',exact=True).click()
    expect(user.locator('#attendance-status')).to_have_text('Đang nghỉ trưa')
    user.get_by_role('button',name='TIẾP TỤC REMOTE',exact=True).click()
    user.locator('#remote-reason').fill('Pages remote test')
    user.locator('#remote-form button[type="submit"]').click()
    expect(user.locator('#attendance-status')).to_have_text('Đang làm Remote')
    user.reload()
    expect(user.locator('#attendance-status')).to_have_text('Đang làm Remote')
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==2
    assert user.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors
