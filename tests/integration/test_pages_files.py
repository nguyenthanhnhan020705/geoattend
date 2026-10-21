from pathlib import Path

import pytest
from playwright.sync_api import expect
from tests.pages_fixtures import pages_site, login_pages
from tests.integration.test_weekly_reports import PDF, PDF2

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize('width',[360,1280])
def test_cross_origin_pdf_upload_download_and_admin_excel(pages_site,width):
    site=pages_site
    page=site['browser'].new_page(viewport={'width':width,'height':900})
    requests=[]
    page.on('request',lambda request: requests.append(request) if '/api/' in request.url else None)
    login_pages(page,site)
    page.get_by_role('link',name='NỘP BÁO CÁO TUẦN',exact=True).click()
    expect(page.locator('#report-week')).to_contain_text('19/10/2026')
    page.get_by_label('File PDF báo cáo tuần').set_input_files({'name':'Pages.pdf','mimeType':'application/pdf','buffer':PDF})
    page.get_by_role('button',name='Nộp báo cáo',exact=True).click()
    expect(page.locator('#current-report')).to_contain_text('Pages.pdf')
    with page.expect_download() as download:
        page.locator('#current-report').get_by_role('link',name='Tải PDF',exact=True).click()
    assert Path(download.value.path()).read_bytes()==PDF
    page.evaluate('window.open=()=>null')
    with page.expect_download() as download:
        page.locator('#current-report').get_by_role('link',name='Xem PDF',exact=True).click()
    assert Path(download.value.path()).read_bytes()==PDF
    page.route(site['api']+'/api/weekly-reports/*/file*',lambda route:route.fulfill(status=403,content_type='application/json',body='{"message":"Không được đọc"}',headers={'Access-Control-Allow-Origin':site['frontend_origin']}))
    page.locator('#current-report').get_by_role('link',name='Tải PDF',exact=True).click()
    expect(page.locator('#current-report')).to_contain_text('Không được đọc')
    page.unroute(site['api']+'/api/weekly-reports/*/file*')
    admin=site['browser'].new_page(viewport={'width':width,'height':900})
    login_pages(admin,site,'admin','Admin1234')
    admin.get_by_role('link',name='BÁO CÁO TUẦN',exact=True).click()
    expect(admin.locator('#reports-list')).to_contain_text('Pages.pdf')
    with admin.expect_download() as download:
        admin.locator('#reports-list').get_by_role('link',name='Tải PDF',exact=True).click()
    assert Path(download.value.path()).read_bytes()==PDF
    admin.get_by_role('link',name='Dashboard',exact=True).click()
    expect(admin.locator('#export-attendance')).to_be_enabled()
    with admin.expect_download() as download:
        admin.get_by_role('button',name='Xuất Excel',exact=True).click()
    assert Path(download.value.path()).read_bytes().startswith(b'PK')
    for request in requests:
        if request.method!='OPTIONS' and '/auth/token' not in request.url:
            assert request.headers.get('authorization','').startswith('Bearer '),request.url
        assert 'access_token' not in request.url and 'Bearer' not in request.url
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
