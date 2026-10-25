from pathlib import Path
from datetime import datetime, timezone
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_weekly_reports import reports, upload
from tests.pdf_fixtures import text_pdf
from tests.test_pdf_summary_provider import TEXT
from tests.pages_fixtures import pages_site

pytestmark=[pytest.mark.integration,pytest.mark.browser]


@pytest.mark.parametrize('width',[360,1280])
@pytest.mark.parametrize('admin',[False,True])
def test_summary_appears_automatically_beside_file_without_loading_pdf(live_site,reports,migrated_db,width,admin):
    from app.reports import summaries
    client,headers,_,_=reports
    pdf_bytes=text_pdf(pages=2)
    upload(client,headers,pdf=pdf_bytes)
    summaries.discover(migrated_db);job=summaries.claim(migrated_db)
    summaries.finish(migrated_db,job,summary=TEXT.strip())
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':width,'height':900})
        errors=[];requests=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('request',lambda request:requests.append((request.method,request.url)))
        login(page,live_site,'admin' if admin else 'worker','Admin1234' if admin else 'Worker1234')
        page.goto(live_site+('/admin' if admin else '/user')+'/weekly-reports')
        actions=page.locator('.report-actions').first
        expect(actions.locator('a,button')).to_have_text(['Tải PDF','Xem trước PDF'])
        expect(page.get_by_role('button',name='Tóm tắt PDF',exact=True)).to_have_count(0)
        expect(page.get_by_role('button',name='Xem PDF và tóm tắt',exact=True)).to_have_count(0)
        if admin:
            expect(page.locator('.pdf-summary-text').first).to_have_text(TEXT.strip(),timeout=10000)
        else:
            expect(page.locator('.pdf-summary-viewer')).to_have_count(0)
            assert not [url for _,url in requests if '/summary?' in url]
        assert not [url for _,url in requests if '/file?' in url or url.endswith('/file') or '/vendor/pdfjs/' in url]
        if admin:
            layout=page.locator('.report-summary-layout').first
            details=layout.locator('.report-file-details').bounding_box()
            summary=layout.locator('.pdf-summary-viewer').bounding_box()
            if width>700:
                assert summary['x']>=details['x']+details['width']-1
            else:
                assert summary['y']>=details['y']+details['height']-1
        download=actions.get_by_role('link',name='Tải PDF',exact=True)
        preview=actions.get_by_role('link',name='Xem trước PDF',exact=True)
        assert download.get_attribute('href').endswith('/file?download=true')
        assert preview.get_attribute('href')=='#'
        assert preview.get_attribute('target') is None
        if width==1280:
            with page.expect_download() as downloaded:
                download.click()
            assert Path(downloaded.value.path()).read_bytes()==pdf_bytes
        requests.clear()
        if admin:
            expect(page.locator('.pdf-summary-text').first).to_have_text(TEXT.strip(),timeout=10000)
        else:
            expect(page.locator('.pdf-summary-viewer')).to_have_count(0)
        assert page.locator('.pdf-summary-viewer canvas,.pdf-summary-viewer iframe,.pdf-summary-document').count()==0
        assert not [url for _,url in requests if '/file' in url or '/vendor/pdfjs/' in url]
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.reload()
        if admin:
            expect(page.locator('.pdf-summary-text').first).to_have_text(TEXT.strip(),timeout=10000)
        else:
            expect(page.locator('.report-actions').first).to_be_visible()
            expect(page.locator('.pdf-summary-viewer')).to_have_count(0)
            assert not [url for _,url in requests if '/summary?' in url]
        assert not [r for r in requests if r[0]=='POST' and '/summary' in r[1]]
        assert not errors
        artifacts=Path('.local-tests/pdf-summary/screenshots');artifacts.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(artifacts/f'{"admin" if admin else "user"}-{width}.png'),full_page=True)
        browser.close()


def test_failed_retry_updates_automatically_and_removal_stops_polling(live_site,reports,migrated_db):
    from app.reports import summaries
    client,headers,_,_=reports
    upload(client,headers,pdf=text_pdf())
    summaries.discover(migrated_db);job=summaries.claim(migrated_db)
    summaries.finish(migrated_db,job,error_code='UNREADABLE')
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page()
        login(page,live_site,'admin','Admin1234')
        page.goto(live_site+'/admin/weekly-reports')
        expect(page.locator('.pdf-summary-text')).to_have_text('Không thể đọc nội dung tài liệu để tóm tắt')
        page.clock.install()
        page.get_by_role('button',name='Tạo lại',exact=True).click()
        expect(page.locator('.pdf-summary-text')).to_have_text('Đang tạo bản tóm tắt...')
        page.clock.fast_forward(3001)
        expect(page.locator('.pdf-summary-text')).to_have_text('Đang tạo bản tóm tắt...')
        calls=[];page.on('request',lambda req:calls.append(req.url) if '/summary?' in req.url else None)
        page.locator('#reports-list').evaluate('(list)=>list.replaceChildren()')
        page.clock.fast_forward(20000)
        assert not calls
        browser.close()


def test_summary_does_not_pair_with_pdf_replaced_after_list_loaded(live_site,reports):
    client,headers,_,_=reports
    upload(client,headers,pdf=text_pdf())
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page()
        login(page,live_site,'admin','Admin1234')
        page.goto(live_site+'/admin/weekly-reports')
        expect(page.locator('.pdf-summary-text').first).to_contain_text('Chưa tạo')
        page.clock.install()
        upload(client,headers,revision=1,pdf=text_pdf('Different content'))
        page.clock.fast_forward(3001)
        expect(page.locator('.pdf-summary-text').first).to_contain_text('PDF đã thay đổi')
        assert page.locator('.pdf-summary-viewer canvas').count()==0
        browser.close()


def test_admin_shows_each_reports_summary_independently(live_site,reports,migrated_db):
    from app.reports import summaries
    from tests.test_auth_api import signin
    client,headers,_,_=reports
    first=upload(client,headers,pdf=text_pdf(),filename='First.pdf').json()['id']
    csrf=signin(client,'other','Worker1234').json()['csrf_token']
    second=upload(client,{'X-CSRF-Token':csrf},pdf=text_pdf('Other report'),filename='Second.pdf').json()['id']
    expected={first:'Nội dung báo cáo thứ nhất.',second:'Nội dung báo cáo thứ hai.'}
    summaries.discover(migrated_db)
    for _ in range(2):
        job=summaries.claim(migrated_db)
        summaries.finish(migrated_db,job,summary=expected[str(job['report_id'])])
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page()
        login(page,live_site,'admin','Admin1234')
        page.goto(live_site+'/admin/weekly-reports')
        expect(page.locator('.pdf-summary-text')).to_have_count(2)
        for filename,text in [('First.pdf',expected[first]),('Second.pdf',expected[second])]:
            row=page.locator('.report-summary-layout').filter(has=page.get_by_text(filename,exact=True))
            expect(row.locator('.pdf-summary-text')).to_have_text(text)
        page.get_by_role('button',name='Xem báo cáo',exact=True).click()
        expect(page.locator('.pdf-summary-text')).to_have_count(2)
        for text in expected.values():
            expect(page.get_by_text(text,exact=True)).to_be_visible()
        browser.close()


def test_pages_user_uploads_but_only_admin_sees_automatic_summary(pages_site,migrated_db):
    from tests.pages_fixtures import login_pages
    from app.reports import summaries
    site=pages_site
    page=site['browser'].new_page(viewport={'width':360,'height':850})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    # Only this new Pages test aligns its browser with the fixture's server.
    page.clock.install(time=datetime(2026,10,21,2,tzinfo=timezone.utc))
    login_pages(page,site)
    page.goto(site['url']+'/user/weekly-reports/')
    page.get_by_label('File PDF báo cáo tuần').set_input_files({'name':'Scan-test.pdf','mimeType':'application/pdf','buffer':text_pdf()})
    page.get_by_role('button',name='Nộp báo cáo',exact=True).click()
    expect(page.locator('#report-message')).to_contain_text('Đã nộp')
    summaries.discover(migrated_db);job=summaries.claim(migrated_db)
    summaries.finish(migrated_db,job,summary=TEXT.strip())
    requests=[];page.on('request',lambda request:requests.append(request.url))
    page.clock.fast_forward(3001)
    expect(page.locator('.pdf-summary-viewer')).to_have_count(0)
    assert not [url for url in requests if '/summary?' in url]
    admin_page=site['browser'].new_page(viewport={'width':360,'height':850})
    admin_page.clock.install(time=datetime(2026,10,21,2,tzinfo=timezone.utc))
    login_pages(admin_page,site,'admin','Admin1234')
    admin_page.goto(site['url']+'/admin/weekly-reports/')
    expect(admin_page.locator('.pdf-summary-text')).to_have_text(TEXT.strip(),timeout=10000)
    assert admin_page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert page.locator('.pdf-summary-viewer canvas').count()==0
    assert not [url for url in requests if '/file' in url or '/vendor/pdfjs/' in url]
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors
