from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright,expect
from tests.integration.test_browser import live_site,login
from tests.integration.test_weekly_reports import reports,upload

pytestmark=[pytest.mark.integration,pytest.mark.browser]


@pytest.mark.parametrize('width',[360,1280])
def test_admin_week_navigation_keeps_employee_and_shows_missing_weeks(live_site,reports,width):
    client,headers,_,ids=reports
    assert upload(client,headers).status_code==200
    with sync_playwright() as p:
        channel='msedge' if Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe').exists() else None
        browser=p.chromium.launch(channel=channel,headless=True)
        page=browser.new_page(viewport={'width':width,'height':850})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        login(page,live_site,'admin','Admin1234')
        page.goto(live_site+'/admin/weekly-reports')
        expect(page.locator('#filter-week')).to_have_value('2026-10-19')
        page.get_by_label('Nhân viên',exact=True).select_option(ids[0])
        page.get_by_role('button',name='Xem báo cáo',exact=True).click()
        expect(page.locator('#reports-list > li')).to_have_count(1)
        expect(page.locator('#reports-list')).to_contain_text('Đã nộp')
        page.get_by_role('button',name='Tuần trước',exact=True).click(timeout=3000)
        expect(page.locator('#admin-report-week')).to_have_text('Tuần 12/10/2026 – 18/10/2026')
        expect(page.locator('#filter-user')).to_have_value(ids[0])
        expect(page.locator('#reports-list > li')).to_have_count(1)
        expect(page.locator('#reports-list')).to_contain_text('Quá hạn chưa nộp')
        page.get_by_role('button',name='Tuần sau',exact=True).click()
        expect(page.locator('#admin-report-week')).to_have_text('Tuần 19/10/2026 – 25/10/2026')
        expect(page.locator('#reports-list')).to_contain_text('Đã nộp')
        # An arbitrary Sunday uses its reporting week, including year rollover.
        page.locator('#filter-week').fill('2027-01-03')
        page.get_by_role('button',name='Tuần trước',exact=True).click()
        expect(page.locator('#filter-week')).to_have_value('2026-12-21')
        page.get_by_role('button',name='Tuần sau',exact=True).click()
        expect(page.locator('#filter-week')).to_have_value('2026-12-28')
        expect(page.locator('#filter-user')).to_have_value(ids[0])
        expect(page.locator('#reports-list')).to_contain_text('Chưa nộp')
        # Two clicks before either response must still advance two weeks.
        page.evaluate("() => { document.getElementById('report-week-prev').click(); document.getElementById('report-week-prev').click(); }")
        expect(page.locator('#admin-report-week')).to_have_text('Tuần 14/12/2026 – 20/12/2026')
        page.get_by_label('Nhân viên',exact=True).select_option('')
        page.get_by_role('button',name='Xem báo cáo',exact=True).click()
        expect(page.locator('#reports-list > li')).to_have_count(2)
        page.get_by_role('button',name='Tuần trước',exact=True).click()
        expect(page.locator('#admin-report-week')).to_have_text('Tuần 07/12/2026 – 13/12/2026')
        expect(page.locator('#reports-list > li')).to_have_count(2)
        expect(page.locator('#reports-page')).to_have_text('1 / 1')
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        assert errors==[]
        browser.close()
