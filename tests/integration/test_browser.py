from tests.browser_navigation import choose_menu, open_menu
from pathlib import Path
import os
import socket
import threading
import time
import pytest
from playwright.sync_api import sync_playwright, expect

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.fixture
def live_site(api_client,test_dsn):
    import uvicorn
    from app.main import create_app
    from app.config import Settings
    from app.db.pool import make_pool
    sock = socket.socket()
    sock.bind(('127.0.0.1',0))
    port = sock.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    pool = make_pool(test_dsn)
    pool.open()
    server = uvicorn.Server(uvicorn.Config(create_app(Settings(origin=origin),pool),log_level='error'))
    thread = threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(.05)
    assert server.started
    yield origin
    server.should_exit = True
    thread.join(10)
    pool.close()
    sock.close()


def login(page, origin, username, password):
    page.goto(origin+'/login')
    page.get_by_label('Tên tài khoản',exact=True).fill(username)
    page.get_by_label('Mật khẩu',exact=True).fill(password)
    page.get_by_role('button',name='Đăng nhập').click()
    page.wait_for_url('**/admin/users' if username=='admin' else '**/user')


def test_account_browser_flow_mobile_xss(live_site):
    artifacts = Path('.superpowers/sdd/2026-10-14-phase-1-foundation-auth/artifacts')
    artifacts.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        default = 'msedge' if Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe').exists() else 'chromium'
        channel = os.getenv('GEOATTEND_BROWSER_CHANNEL',default)
        browser = p.chromium.launch(channel=None if channel=='chromium' else channel,headless=True)
        admin_context = browser.new_context(viewport={'width':1280,'height':900})
        admin = admin_context.new_page()
        errors = []
        admin.on('pageerror',lambda error:errors.append(str(error)))
        login(admin,live_site,'admin','Admin1234')
        admin.get_by_label('Họ và tên').fill('<img src=x onerror=alert(1)>')
        admin.get_by_label('Tên tài khoản',exact=True).fill('nhan')
        admin.get_by_label('Mật khẩu ban đầu').fill('User1234')
        admin.get_by_role('button',name='Tạo tài khoản').click()
        expect(admin.locator('#users li')).to_have_count(1)
        expect(admin.locator('#users strong')).to_have_text('<img src=x onerror=alert(1)>')
        assert admin.locator('#users img').count() == 0
        admin.screenshot(path=str(artifacts/'admin-desktop.png'),full_page=True)
        user_context = browser.new_context(viewport={'width':360,'height':800})
        user = user_context.new_page()
        user.on('pageerror',lambda error:errors.append(str(error)))
        login(user,live_site,'nhan','User1234')
        expect(user.locator('#full-name')).to_have_text('<img src=x onerror=alert(1)>')
        assert user.locator('img').count() == 0
        assert user.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        user.screenshot(path=str(artifacts/'user-mobile.png'),full_page=True)
        choose_menu(user, 'Đổi mật khẩu')
        user.get_by_label('Mật khẩu hiện tại').fill('User1234')
        user.get_by_label('Mật khẩu mới',exact=True).fill('Changed123')
        user.get_by_label('Nhập lại mật khẩu mới').fill('Changed123')
        user.get_by_role('button',name='Lưu mật khẩu mới').click()
        user.wait_for_url('**/login')
        login(user,live_site,'nhan','Changed123')
        admin.get_by_role('button',name='Cấp lại mật khẩu').click()
        admin.get_by_label('Mật khẩu mới',exact=True).fill('Reset1234')
        admin.get_by_role('button',name='Đặt lại mật khẩu').click()
        expect(admin.locator('#reset-dialog')).not_to_be_visible()
        user.reload()
        user.wait_for_url('**/login')
        login(user,live_site,'nhan','Reset1234')
        admin.set_viewport_size({'width':360,'height':800})
        assert admin.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        admin.screenshot(path=str(artifacts/'admin-mobile.png'),full_page=True)
        open_menu(user)
        user.get_by_role('button',name='Đăng xuất').click()
        user.wait_for_url('**/login')
        assert errors == []
        browser.close()
