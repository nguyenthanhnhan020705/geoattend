from pathlib import Path
import os
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_weekly_reports import reports, PDF, PDF2

pytestmark=[pytest.mark.integration,pytest.mark.browser]


@pytest.mark.parametrize('width',[360,1280])
def test_user_submit_replace_and_admin_view(live_site,reports,width):
    with sync_playwright() as p:
        channel=os.getenv('GEOATTEND_BROWSER_CHANNEL','msedge' if Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe').exists() else 'chromium')
        browser=p.chromium.launch(channel=None if channel=='chromium' else channel,headless=True)
        page=browser.new_page(viewport={'width':width,'height':850})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        login(page,live_site,'worker','Worker1234')
        page.get_by_role('link',name='Nộp báo cáo tuần',exact=True).click()
        expect(page.locator('#report-week')).to_contain_text('19/10/2026')
        page.get_by_label('File PDF báo cáo tuần').set_input_files({'name':'Báo cáo.pdf','mimeType':'application/pdf','buffer':PDF})
        page.get_by_role('button',name='Nộp báo cáo',exact=True).click()
        expect(page.locator('#report-message')).to_contain_text('Đã nộp')
        expect(page.locator('#current-report')).to_contain_text('Báo cáo.pdf')
        page.get_by_label('File PDF báo cáo tuần').set_input_files({'name':'Bản mới.pdf','mimeType':'application/pdf','buffer':PDF2})
        decisions=[False,True]
        page.on('dialog',lambda dialog:dialog.accept() if decisions.pop(0) else dialog.dismiss())
        with page.expect_event('dialog'):
            page.get_by_role('button',name='Thay thế báo cáo',exact=True).click()
        expect(page.get_by_role('button',name='Thay thế báo cáo',exact=True)).to_be_enabled()
        expect(page.locator('#current-report')).to_contain_text('Báo cáo.pdf')
        with page.expect_event('dialog'):
            page.get_by_role('button',name='Thay thế báo cáo',exact=True).click()
        expect(page.locator('#current-report')).to_contain_text('Bản mới.pdf')
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        artifacts=Path('.local-tests/weekly-reports/screenshots');artifacts.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(artifacts/f'user-{width}.png'),full_page=True)
        with page.expect_download() as download:
            page.locator('#current-report').get_by_role('link',name='Tải PDF').click()
        assert Path(download.value.path()).read_bytes()==PDF2
        admin=browser.new_page(viewport={'width':width,'height':850})
        login(admin,live_site,'admin','Admin1234')
        admin.get_by_role('link',name='Nhân viên báo cáo tuần',exact=True).click()
        expect(admin.locator('#reports-list')).to_contain_text('Bản mới.pdf')
        expect(admin.locator('#reports-list')).to_contain_text('Chưa nộp')
        admin.get_by_label('Nhân viên').select_option(label='Nhân viên worker · worker')
        admin.get_by_role('button',name='Xem báo cáo').click()
        expect(admin.locator('#reports-list > li')).to_have_count(1)
        assert admin.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        admin.screenshot(path=str(artifacts/f'admin-{width}.png'),full_page=True)
        assert errors==[]
        browser.close()


def test_home_reminders_and_week_rollover(live_site,reports,migrated_db):
    from datetime import datetime,timezone
    _,_,clock,_=reports
    clock['now']=datetime(2026,10,25,2,tzinfo=timezone.utc)
    with sync_playwright() as p:
        channel='msedge' if Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe').exists() else None
        browser=p.chromium.launch(channel=channel,headless=True)
        page=browser.new_page()
        login(page,live_site,'worker','Worker1234')
        expect(page.locator('[data-report-notices]')).to_contain_text('BẠN CÒN 1 NGÀY ĐỂ NỘP BÁO CÁO NHÉ!!')
        expect(page.locator('[data-report-notices]')).to_contain_text('TUẦN VỪA RỒI BẠN CHƯA NỘP BÁO CÁO.')
        page.get_by_role('link',name='Nộp báo cáo tuần',exact=True).click()
        expect(page.locator('#report-week')).to_contain_text('19/10/2026')
        page.get_by_label('File PDF báo cáo tuần').set_input_files({'name':'Old week.pdf','mimeType':'application/pdf','buffer':PDF})
        # Keep auth stable while this test changes only the reporting clock.
        migrated_db.execute("UPDATE geoattend.auth_sessions SET expires_at='2026-10-27 00:00+00'")
        migrated_db.commit()
        clock['now']=datetime(2026,10,25,17,tzinfo=timezone.utc)
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        expect(page.locator('#report-week')).to_contain_text('26/10/2026')
        expect(page.locator('[data-report-notices]')).not_to_contain_text('BẠN CÒN 1 NGÀY')
        assert page.get_by_label('File PDF báo cáo tuần').evaluate('(input)=>input.files.length')==0
        browser.close()


def test_ambiguous_upload_retries_same_request(live_site,reports,migrated_db):
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge' if Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe').exists() else None,headless=True)
        page=browser.new_page()
        login(page,live_site,'worker','Worker1234')
        page.get_by_role('link',name='Nộp báo cáo tuần',exact=True).click()
        expect(page.locator('#report-week')).to_contain_text('19/10/2026')
        requests=[]
        def lose_response(route):
            if route.request.method=='PUT':
                requests.append(route.request.url)
                if len(requests)==1:
                    response=route.fetch()
                    assert response.status==200
                    route.abort()
                else:route.continue_()
            else:route.continue_()
        page.route('**/api/weekly-reports/**',lose_response)
        page.get_by_label('File PDF báo cáo tuần').set_input_files({'name':'Retry.pdf','mimeType':'application/pdf','buffer':PDF})
        page.get_by_role('button',name='Nộp báo cáo',exact=True).click()
        expect(page.get_by_role('button',name='Gửi lại báo cáo')).to_be_visible()
        page.get_by_role('button',name='Gửi lại báo cáo').click()
        expect(page.locator('#report-message')).to_contain_text('Đã nộp')
        assert len(requests)==2 and requests[0]==requests[1]
        assert migrated_db.execute('SELECT revision FROM geoattend.weekly_reports').fetchone()['revision']==1
        browser.close()


@pytest.mark.parametrize('case',['week','account'])
def test_rejected_pending_requires_file_reselection(live_site,reports,migrated_db,case):
    from datetime import datetime,timezone
    _,_,clock,_=reports
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge' if Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe').exists() else None,headless=True)
        page=browser.new_page()
        login(page,live_site,'worker','Worker1234')
        page.get_by_role('link',name='Nộp báo cáo tuần',exact=True).click()
        expect(page.locator('#report-week')).to_contain_text('19/10/2026')
        def fail_before_commit(route):
            if route.request.method=='PUT':route.abort()
            else:route.continue_()
        page.route('**/api/weekly-reports/**',fail_before_commit)
        page.get_by_label('File PDF báo cáo tuần').set_input_files({'name':'Never committed.pdf','mimeType':'application/pdf','buffer':PDF})
        page.get_by_role('button',name='Nộp báo cáo',exact=True).click()
        expect(page.get_by_role('button',name='Gửi lại báo cáo')).to_be_visible()
        expect(page.locator('#report-message')).to_contain_text('Chưa xác nhận')
        expect(page.get_by_role('button',name='Gửi lại báo cáo')).to_be_enabled()
        page.unroute('**/api/weekly-reports/**',fail_before_commit)
        if case=='week':
            migrated_db.execute("UPDATE geoattend.auth_sessions SET expires_at='2026-10-27 00:00+00'");migrated_db.commit()
            clock['now']=datetime(2026,10,25,17,tzinfo=timezone.utc)
            page.evaluate("window.dispatchEvent(new Event('focus'))")
            expect(page.locator('#report-week')).to_contain_text('26/10/2026')
        else:
            response=page.request.post(live_site+'/api/auth/login',data={'username':'other','password':'Worker1234'})
            assert response.status==200
        page.get_by_role('button',name='Gửi lại báo cáo').click()
        expect(page.get_by_role('button',name='Gửi lại báo cáo')).not_to_be_visible()
        assert page.get_by_label('File PDF báo cáo tuần').evaluate('(input)=>input.files.length')==0
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.weekly_reports').fetchone()['n']==0
        browser.close()
