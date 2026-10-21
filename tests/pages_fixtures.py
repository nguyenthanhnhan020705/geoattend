import functools
import http.server
import socket
import threading
import time
from datetime import datetime, timezone

import pytest
from playwright.sync_api import sync_playwright

from app.config import Settings
from app.main import create_app
from scripts.build_pages import build_pages


@pytest.fixture
def pages_site(api_client, migrated_db, tmp_path, monkeypatch):
    import uvicorn
    now = datetime(2026, 10, 21, 2, tzinfo=timezone.utc)
    monkeypatch.setattr('app.clock.utc_now', lambda: now)
    monkeypatch.setattr('app.auth.dependencies.utc_now', lambda: now)
    monkeypatch.setattr('app.auth.routes.utc_now', lambda: now)
    from app.accounts.service import create_user
    user = create_user(migrated_db, 'worker', 'Nhân viên Pages', 'Worker1234')
    migrated_db.execute('UPDATE geoattend.profiles SET created_at=%s', (now,))
    migrated_db.execute('UPDATE geoattend.schema_migrations SET applied_at=%s', (now,))
    migrated_db.commit()
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=str(tmp_path / 'public'))
    static = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    static_origin = f'http://localhost:{static.server_port}'
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    api_origin = f'http://127.0.0.1:{sock.getsockname()[1]}'
    build_pages(tmp_path / 'public/geoattend', base_path='/geoattend/', api_origin=api_origin,
                version='browser-test', allow_loopback=True)
    server = uvicorn.Server(uvicorn.Config(create_app(Settings(origin=api_origin,
        frontend_origin=static_origin), api_client.app.state.pool), log_level='error'))
    api_thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    static_thread = threading.Thread(target=static.serve_forever, daemon=True)
    static_thread.start()
    api_thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(.05)
    assert server.started
    try:
        with sync_playwright() as p:
            from pathlib import Path
            channel = 'msedge' if Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe').exists() else None
            browser = p.chromium.launch(channel=channel, headless=True)
            yield dict(browser=browser, url=static_origin+'/geoattend', api=api_origin,
                       public=tmp_path / 'public/geoattend', user_id=str(user.id),
                       frontend_origin=static_origin)
            browser.close()
    finally:
        static.shutdown()
        static.server_close()
        static_thread.join(5)
        server.should_exit = True
        api_thread.join(10)
        sock.close()


def login_pages(page, site, username='worker', password='Worker1234'):
    page.goto(site['url']+'/login/')
    page.get_by_label('Tên tài khoản', exact=True).fill(username)
    page.get_by_label('Mật khẩu', exact=True).fill(password)
    page.get_by_role('button', name='Đăng nhập', exact=True).click()
    page.wait_for_url('**/admin/users/' if username == 'admin' else '**/user/')
