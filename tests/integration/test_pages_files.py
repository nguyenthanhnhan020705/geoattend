from tests.browser_navigation import choose_menu, open_menu
from pathlib import Path
from datetime import datetime,timezone

import pytest
from playwright.sync_api import expect
from tests.pages_fixtures import pages_site, login_pages
from tests.integration.test_weekly_reports import PDF, PDF2
from tests.pdf_fixtures import text_pdf

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize('width',[360,1280])
def test_cross_origin_pdf_upload_download_and_admin_excel(pages_site,width):
    site=pages_site
    page=site['browser'].new_page(viewport={'width':width,'height':900})
    page.clock.install(time=datetime(2026,10,21,2,tzinfo=timezone.utc))
    requests=[]
    page.on('request',lambda request: requests.append(request) if '/api/' in request.url else None)
    login_pages(page,site)
    choose_menu(page, 'Nộp báo cáo tuần')
    expect(page.locator('#report-week')).to_contain_text('19/10/2026')
    pdf=text_pdf(pages=2)
    page.get_by_label('File PDF báo cáo tuần').set_input_files({'name':'Pages.pdf','mimeType':'application/pdf','buffer':pdf})
    page.get_by_role('button',name='Nộp báo cáo',exact=True).click()
    expect(page.locator('#current-report')).to_contain_text('Pages.pdf')
    with page.expect_download() as download:
        page.locator('#current-report').get_by_role('link',name='Tải PDF',exact=True).click()
    assert Path(download.value.path()).read_bytes()==pdf
    page.evaluate("() => { window.open=()=>{throw new Error('Preview must stay inline')}; }")
    page.locator('#current-report').get_by_role('link',name='Xem trước PDF',exact=True).click()
    expect(page.locator('.report-pdf-preview canvas')).to_have_attribute('data-page','1',timeout=15000)
    page.route(site['api']+'/api/weekly-reports/*/file*',lambda route:route.fulfill(status=403,content_type='application/json',body='{"message":"Không được đọc"}',headers={'Access-Control-Allow-Origin':site['frontend_origin']}))
    page.locator('#current-report').get_by_role('link',name='Tải PDF',exact=True).click()
    expect(page.locator('#current-report')).to_contain_text('Không được đọc')
    page.unroute(site['api']+'/api/weekly-reports/*/file*')
    admin=site['browser'].new_page(viewport={'width':width,'height':900})
    admin.clock.install(time=datetime(2026,10,21,2,tzinfo=timezone.utc))
    login_pages(admin,site,'admin','Admin1234')
    choose_menu(admin, 'Nhân viên báo cáo tuần')
    expect(admin.locator('#reports-list')).to_contain_text('Pages.pdf')
    with admin.expect_download() as download:
        admin.locator('#reports-list').get_by_role('link',name='Tải PDF',exact=True).click()
    assert Path(download.value.path()).read_bytes()==pdf
    choose_menu(admin, 'Quản lý nhân viên')
    expect(admin.locator('#export-attendance')).to_be_enabled()
    with admin.expect_download() as download:
        admin.get_by_role('button',name='Xuất Excel',exact=True).click()
    assert Path(download.value.path()).read_bytes().startswith(b'PK')
    for request in requests:
        if request.method!='OPTIONS' and '/auth/token' not in request.url:
            assert request.headers.get('authorization','').startswith('Bearer '),request.url
        assert 'access_token' not in request.url and 'Bearer' not in request.url
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')


def test_pdf_timeout_stays_inline_and_keeps_download_available(pages_site):
    site=pages_site
    page=site['browser'].new_page()
    page.clock.install(time=datetime(2026,10,21,2,tzinfo=timezone.utc))
    login_pages(page,site)
    choose_menu(page, 'Nộp báo cáo tuần')
    expect(page.locator('#report-week')).to_contain_text('19/10/2026')
    page.get_by_label('File PDF báo cáo tuần').set_input_files({'name':'Timeout.pdf','mimeType':'application/pdf','buffer':PDF})
    page.get_by_role('button',name='Nộp báo cáo',exact=True).click()
    expect(page.locator('#current-report')).to_contain_text('Timeout.pdf')
    stalled=[]
    def stall(route):
        if route.request.method=='OPTIONS':route.continue_()
        else:stalled.append(route)
    page.route(site['api']+'/api/weekly-reports/*/file*',stall)
    page.locator('#current-report').get_by_role('link',name='Xem trước PDF',exact=True).click()
    expect(page.locator('#current-report')).to_contain_text('Đang tải PDF')
    page.clock.fast_forward(30001)
    expect(page.locator('#current-report')).to_contain_text('quá thời gian')
    assert len(page.context.pages)==1
    expect(page.locator('#current-report').get_by_role('link',name='Xem trước PDF',exact=True)).not_to_have_attribute('aria-disabled','true')
    page.unroute(site['api']+'/api/weekly-reports/*/file*')
    with page.expect_download() as download:
        page.locator('#current-report').get_by_role('link',name='Tải PDF',exact=True).click()
    assert Path(download.value.path()).read_bytes()==PDF
