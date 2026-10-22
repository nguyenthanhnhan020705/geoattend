"""Browser checks of real frontend assets with isolated, read-only API fixtures."""
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright, expect
from scripts.build_pages import build_pages
from tests.integration.test_mobile_bottom_navigation import check_bottom_bar

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'http://preview.geoattend.test'


@pytest.fixture
def preview(tmp_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)

        def make(width=390, role='USER', pages=False, path='/user'):
            page = browser.new_page(viewport={'width':width, 'height':850})
            source = ROOT / 'app/static'
            base = ''
            if pages:
                source = tmp_path / 'public'
                build_pages(source, base_path='/geoattend/', api_origin='https://api.preview.test', version='preview')
                base = '/geoattend'
                page.add_init_script("sessionStorage.setItem('geoattend:https://api.preview.test:/geoattend/:session',JSON.stringify({token:'preview_token_12345678901234567890',expiresAt:'2099-01-01T00:00:00Z'}))")
            account = {'id':'preview', 'username':'preview', 'full_name':'Nhân viên', 'role':role, 'csrf_token':'preview'}
            data = {
                '/api/auth/me':account,
                '/api/attendance/status':{'work_date':'2026-10-22','status':'NOT_STARTED','revision':0,'allowed_actions':['START_OFFICE','START_REMOTE','MORNING_LEAVE','FULL_DAY_LEAVE'],'open_session':None,'day_finished':False},
                '/api/attendance/history':{'items':[],'total':0,'page':1,'page_size':20},
                '/api/weekly-reports/status':{'notices':[],'week_start':'2026-10-19','week_end':'2026-10-25','report':None,'server_time':'2026-10-22T03:00:00Z'},
                '/api/weekly-reports':{'items':[],'total':0,'page':1,'page_size':20},
            }
            routes = {'/user':'user.html','/account':'account.html','/user/weekly-reports':'user-weekly-reports.html','/login':'login.html'}

            def serve(route):
                path = urlsplit(route.request.url).path
                if path.startswith('/api/'):
                    if path == '/api/auth/logout':
                        route.fulfill(status=204); return
                    route.fulfill(content_type='application/json',body=json.dumps(data.get(path,{})),headers={'Access-Control-Allow-Origin':ORIGIN})
                    return
                if pages:
                    relative = path.removeprefix(base).lstrip('/')
                    file = source / relative
                    if file.is_dir(): file = file / 'index.html'
                else:
                    file = source / (path.removeprefix('/static/') if path.startswith('/static/') else routes.get(path,''))
                if not file.is_file():
                    route.fulfill(status=404); return
                mime = 'text/javascript' if file.suffix == '.js' else mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
                route.fulfill(content_type=mime,body=file.read_bytes())

            page.route('**/*', serve)
            page.goto(ORIGIN + base + path + ('/' if pages else ''))
            return page, base

        yield make
        browser.close()


@pytest.mark.parametrize('width', [320, 390, 430])
def test_preview_mobile_bottom_navigation(preview, width):
    page, _ = preview(width)
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
    page.evaluate('scrollTo(0,document.documentElement.scrollHeight)')
    button = page.locator('#password-form button').bounding_box()
    assert button['y'] + button['height'] <= page.locator('.app-sidebar').bounding_box()['y']
    artifacts = ROOT / '.local-tests/mobile-bottom-navigation'; artifacts.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(artifacts / f'preview-account-{width}.png'),full_page=True)
    page.get_by_role('link', name='Trang chủ chấm công', exact=True).click()
    expect(page.locator('.attendance-panel')).to_be_visible()
    check_bottom_bar(page, width)
    page.screenshot(path=str(artifacts / f'preview-home-{width}.png'),full_page=True)
    page.get_by_role('button',name='Đăng xuất',exact=True).click()
    page.wait_for_url('**/login')


def test_preview_pages_mobile_navigation(preview):
    page, _ = preview(pages=True)
    check_bottom_bar(page, 390)
    for image in page.locator('.mobile-nav-icon img').all():
        assert '/geoattend/static/images/navigation/' in image.get_attribute('src')
    page.get_by_role('link', name='Nộp báo cáo tuần', exact=True).click()
    expect(page.locator('#report-form')).to_be_visible()
    check_bottom_bar(page, 390)


def test_preview_desktop_sidebar_and_resizing(preview):
    page, _ = preview(width=1280)
    expect(page.locator('#sidebar-toggle')).to_be_visible()
    assert page.locator('.app-sidebar').bounding_box()['width'] == 248
    page.get_by_role('link',name='Lịch sử cá nhân',exact=True).click()
    expect(page.locator('.app-sidebar nav')).to_be_visible()
    assert page.locator('.app-sidebar').bounding_box()['width'] == 88
    page.set_viewport_size({'width':390,'height':850})
    check_bottom_bar(page, 390)
    page.set_viewport_size({'width':1280,'height':850})
    expect(page.locator('.app-sidebar nav')).to_be_visible()
    assert page.locator('.app-sidebar').bounding_box()['width'] == 88
    page.get_by_role('button',name='Mở menu',exact=True).click()
    expect(page.get_by_role('link',name='Lịch sử cá nhân',exact=True)).to_be_visible()


def test_preview_admin_account_uses_mobile_bottom_bar(preview):
    page, _ = preview(width=390,role='ADMIN',path='/account')
    expect(page.locator('body')).to_have_attribute('data-navigation-role','ADMIN')
    expect(page.locator('#sidebar-toggle')).to_be_hidden()
    assert page.locator('.app-sidebar').bounding_box()['width'] == 390
    expect(page.locator('nav a[aria-current="page"]')).to_have_text('Tài khoản cá nhân')
