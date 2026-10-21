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
