from datetime import datetime,timezone
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright,expect
from tests.integration.test_browser import live_site,login
from tests.integration.test_weekly_reports import reports,upload
from tests.pdf_fixtures import text_pdf
from tests.pages_fixtures import pages_site,login_pages

pytestmark=[pytest.mark.integration,pytest.mark.browser]


@pytest.mark.parametrize('admin',[False,True])
@pytest.mark.parametrize('width',[360,1280])
def test_preview_is_inline_paginated_and_does_not_open_a_tab(live_site,reports,width,admin):
    client,headers,_,_=reports
    pdf=text_pdf(pages=2)
    upload(client,headers,pdf=pdf)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':width,'height':900})
        errors=[];files=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('request',lambda request:files.append(request.url) if '/file?expected_revision=' in request.url else None)
        login(page,live_site,'admin' if admin else 'worker','Admin1234' if admin else 'Worker1234')
        page.goto(live_site+('/admin' if admin else '/user')+'/weekly-reports')
        actions=page.locator('.report-actions').first
        preview=actions.get_by_role('link',name='Xem trước PDF',exact=True)
        expect(preview).to_be_visible()
        assert not files
        original=page.url
        preview.click()
        box=page.locator('.report-pdf-preview')
        expect(box.locator('canvas')).to_have_attribute('data-page','1',timeout=15000)
        assert page.url==original and len(browser.contexts[0].pages)==1
        assert box.bounding_box()['y']>=actions.bounding_box()['y']+actions.bounding_box()['height']
        assert box.locator('.report-pdf-scroll').bounding_box()['height']<=421
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        expect(preview).to_have_attribute('aria-expanded','true')
        box.get_by_role('button',name='Trang sau PDF',exact=True).click()
        expect(box.locator('canvas')).to_have_attribute('data-page','2')
        box.get_by_role('button',name='Trang trước PDF',exact=True).click()
        expect(box.locator('canvas')).to_have_attribute('data-page','1')
        with page.expect_download() as download:
            actions.get_by_role('link',name='Tải PDF',exact=True).click()
        assert Path(download.value.path()).read_bytes()==pdf
        box.get_by_role('button',name='Đóng xem trước',exact=True).click()
        expect(box).to_have_count(0)
        expect(preview).to_have_attribute('aria-expanded','false')
        preview.click()
        expect(page.locator('.report-pdf-preview canvas')).to_have_attribute('data-page','1',timeout=15000)
        preview.click()
        expect(page.locator('.report-pdf-preview')).to_have_count(0)
        assert len(files)==2 and all('expected_revision=1' in url for url in files)
        assert not errors
        browser.close()


def test_stale_pdf_is_not_rendered_inline(live_site,reports):
    client,headers,_,_=reports
    upload(client,headers,pdf=text_pdf())
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page()
        login(page,live_site,'worker','Worker1234')
        page.goto(live_site+'/user/weekly-reports')
        preview=page.get_by_role('link',name='Xem trước PDF',exact=True).first
        expect(preview).to_be_visible()
        upload(client,headers,revision=1,pdf=text_pdf('Replacement'))
        preview.click()
        expect(page.locator('.report-pdf-status')).to_contain_text('đã được thay thế')
        assert page.locator('.report-pdf-preview canvas').evaluate('(canvas)=>canvas.width')==0
        browser.close()


def test_pages_inline_preview_sends_bearer_and_never_opens_a_window(pages_site):
    site=pages_site
    page=site['browser'].new_page(viewport={'width':360,'height':850})
    page.clock.install(time=datetime(2026,10,21,2,tzinfo=timezone.utc))
    login_pages(page,site)
    page.goto(site['url']+'/user/weekly-reports/')
    page.get_by_label('File PDF báo cáo tuần').set_input_files({'name':'Inline.pdf','mimeType':'application/pdf','buffer':text_pdf(pages=2)})
    page.get_by_role('button',name='Nộp báo cáo',exact=True).click()
    expect(page.locator('#report-message')).to_contain_text('Đã nộp')
    files=[];errors=[]
    page.on('request',lambda request:files.append(request) if '/file?' in request.url else None)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.evaluate("() => { window.open=()=>{throw new Error('Preview must not open a window')}; }")
    page.locator('#current-report').get_by_role('link',name='Xem trước PDF',exact=True).click()
    expect(page.locator('.report-pdf-preview canvas')).to_have_attribute('data-page','1',timeout=15000)
    assert len(files)==1 and files[0].headers.get('authorization','').startswith('Bearer ')
    assert 'Bearer' not in files[0].url and 'access_token' not in files[0].url
    assert page.locator('.pdf-summary-viewer').count()==0
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors
