from tests.browser_navigation import choose_menu, open_menu
import threading
import hashlib
import random
from uuid import uuid4
import httpx
from psycopg import sql
from psycopg.conninfo import make_conninfo
from fastapi.testclient import TestClient
import pytest
from app.config import Settings
from app.db.migrations import grant_runtime
from app.db.pool import make_pool
from app.main import create_app
from tests.integration.test_browser import live_site
from tests.integration.test_weekly_reports import reports

pytestmark=pytest.mark.integration


def test_unmigrated_runtime_returns_actionable_error_without_reading_pdf(reports,migrated_db,test_dsn):
    role='report_old_runtime_'+uuid4().hex
    migrated_db.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    grant_runtime(migrated_db,role)
    migrated_db.execute(sql.SQL('REVOKE SELECT(name,applied_at) ON geoattend.schema_migrations FROM {}').format(sql.Identifier(role)))
    migrated_db.execute('DROP TABLE geoattend.pdf_summaries')
    migrated_db.execute('DROP TABLE geoattend.weekly_reports')
    migrated_db.execute("DELETE FROM geoattend.schema_migrations WHERE name='005_weekly_reports.sql'")
    migrated_db.commit()
    pool=make_pool(make_conninfo(test_dsn,user=role));pool.open()
    try:
        with TestClient(create_app(Settings(),pool),raise_server_exceptions=False) as client:
            login=client.post('/api/auth/login',json={'username':'worker','password':'Worker1234'})
            headers={'X-CSRF-Token':login.json()['csrf_token'],'X-Report-Filename':'test.pdf','Content-Type':'application/pdf'}
            for path in ['/api/weekly-reports/status','/api/weekly-reports']:
                response=client.get(path)
                assert response.status_code==503
                assert response.json()['code']=='REPORTS_NOT_READY'
            response=client.put('/api/weekly-reports/2026-10-19',params={'request_id':str(uuid4()),'expected_revision':0},headers=headers,content=b'not a PDF')
            # Readiness fails before any file validation/upload work.
            assert response.status_code==503
            assert response.json()['code']=='REPORTS_NOT_READY'
            assert client.get('/api/health').status_code==200
            assert client.get('/api/attendance/status').status_code==200
    finally:
        pool.close()
        migrated_db.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
        migrated_db.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)));migrated_db.commit()


def test_real_http_435mb_upload_keeps_web_responsive(live_site,reports):
    # Real TCP/Uvicorn is needed: TestClient can hide large-body backpressure.
    # Incompressible synthetic bytes also exercise bytea/TOAST at real size.
    pdf=b'%PDF-1.4\n'+random.Random(435).randbytes(4_350_000-15)+b'%%EOF\n'
    assert len(pdf)==4_350_000
    with httpx.Client(base_url=live_site,timeout=12) as client:
        login=client.post('/api/auth/login',json={'username':'worker','password':'Worker1234'})
        assert login.status_code==200
        headers={'X-CSRF-Token':login.json()['csrf_token'],'X-Report-Filename':'large.pdf','Content-Type':'application/pdf'}
        result=[];errors=[]
        def send():
            try:
                result.append(client.put('/api/weekly-reports/2026-10-19',params={'request_id':str(uuid4()),'expected_revision':0},headers=headers,content=pdf))
            except Exception as error:errors.append(type(error).__name__)
        thread=threading.Thread(target=send,daemon=True);thread.start()
        with httpx.Client(base_url=live_site,timeout=3) as health:
            assert health.get('/api/health').status_code==200
        thread.join(15)
        assert not thread.is_alive() and errors==[]
        assert result[0].status_code==200,result[0].text
        metadata=result[0].json()
        assert metadata['size_bytes']==4_350_000
        downloaded=client.get('/api/weekly-reports/'+metadata['id']+'/file').content
        assert len(downloaded)==4_350_000
        assert hashlib.sha256(downloaded).digest()==hashlib.sha256(pdf).digest()


@pytest.mark.browser
def test_unready_reports_disable_file_selection_and_show_real_cause(live_site,reports,migrated_db):
    from pathlib import Path
    from playwright.sync_api import sync_playwright,expect
    from tests.integration.test_browser import login
    migrated_db.execute('DROP TABLE geoattend.pdf_summaries')
    migrated_db.execute('DROP TABLE geoattend.weekly_reports')
    migrated_db.execute("DELETE FROM geoattend.schema_migrations WHERE name='005_weekly_reports.sql'")
    migrated_db.commit()
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge' if Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe').exists() else None,headless=True)
        page=browser.new_page()
        login(page,live_site,'worker','Worker1234')
        choose_menu(page, 'Nộp báo cáo tuần')
        expect(page.locator('#notice-error')).to_contain_text('chưa được kích hoạt')
        expect(page.get_by_label('File PDF báo cáo tuần')).to_be_disabled()
        expect(page.get_by_role('button',name='Nộp báo cáo',exact=True)).to_be_disabled()
        browser.close()
