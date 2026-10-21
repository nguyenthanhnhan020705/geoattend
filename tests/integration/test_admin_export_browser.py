from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.integration.test_browser import live_site, login
from tests.integration.test_office_browser import office_site
from tests.integration.test_admin_dashboard_browser import launch

pytestmark = [pytest.mark.integration, pytest.mark.browser]


@pytest.mark.parametrize('width', [360, 1280])
def test_admin_download_excel_filters_error_and_retry(office_site, migrated_db, width):
    uid = migrated_db.execute("SELECT id FROM geoattend.profiles WHERE username='worker'").fetchone()['id']
    day = migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,'2026-10-14','CHECKED_OUT') RETURNING id", (uid,)).fetchone()['id']
    migrated_db.execute("INSERT INTO geoattend.work_sessions(day_id,work_mode,start_time,end_time,end_source) VALUES(%s,'REMOTE','2026-10-14 02:00+00','2026-10-14 10:00+00','USER')", (day,))
    migrated_db.commit()
    with sync_playwright() as p:
        browser, page = launch(p, width)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        login(page, office_site, 'admin', 'Admin1234')
        page.get_by_role('link', name='Dashboard', exact=True).click()
        expect(page.locator('#export-attendance')).to_be_enabled()
        expect(page.locator('#export-from')).to_have_value('2026-10-08')
        expect(page.locator('#export-to')).to_have_value('2026-10-14')
        page.locator('#export-from').fill('2026-10-14')
        page.locator('#export-user').select_option(str(uid))
        page.route('**/api/admin/attendance/export?*', lambda route: route.fulfill(
            status=503, content_type='application/json', body='{"message":"Database unavailable"}'))
        page.get_by_role('button', name='Xuất Excel', exact=True).click()
        expect(page.locator('#export-message')).to_have_text('Database unavailable')
        expect(page.locator('#export-attendance')).to_be_enabled()
        page.unroute('**/api/admin/attendance/export?*')
        with page.expect_download() as download_info, page.expect_request('**/api/admin/attendance/export?*') as request_info:
            page.get_by_role('button', name='Xuất Excel', exact=True).click()
        download = download_info.value
        assert download.suggested_filename == 'geoattend_2026-10-14_2026-10-14.xlsx'
        assert 'user_id='+str(uid) in request_info.value.url
        assert 'from=2026-10-14' in request_info.value.url and 'to=2026-10-14' in request_info.value.url
        artifacts = Path('.local-tests/excel-export/artifacts'); artifacts.mkdir(parents=True, exist_ok=True)
        download.save_as(artifacts/f'attendance-{width}.xlsx')
        assert (artifacts/f'attendance-{width}.xlsx').read_bytes().startswith(b'PK')
        expect(page.locator('#export-message')).to_have_text('Đã tải file Excel.')
        page.locator('#reload-dashboard').click()
        expect(page.locator('#export-from')).to_have_value('2026-10-14')
        expect(page.locator('#export-user')).to_have_value(str(uid))
        page.locator('#export-from').fill('2026-10-15')
        page.get_by_role('button', name='Xuất Excel', exact=True).click()
        expect(page.locator('#export-message')).to_contain_text('khoảng ngày hợp lệ')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(artifacts/f'export-{width}.png'), full_page=True)
        assert errors == []
        browser.close()
