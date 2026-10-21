from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from uuid import uuid4

import pytest
from tests.integration.test_attendance import employee, action
from tests.test_auth_api import signin

pytestmark = pytest.mark.integration
URL = '/api/admin/attendance/export'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def sheet(response):
    assert response.status_code == 200, response.text[:200] if response.status_code != 200 else ''
    assert response.headers['content-type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert '.xlsx' in response.headers['content-disposition']
    assert response.headers['cache-control'] == 'no-store'
    with ZipFile(BytesIO(response.content)) as archive:
        for name in archive.namelist():
            if name.endswith(('.xml', '.rels')):
                ET.fromstring(archive.read(name))
        root = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        assert not root.findall('.//s:f', NS), 'User input must never become an Excel formula'
        rows = []
        for row in root.findall('s:sheetData/s:row', NS):
            rows.append([''.join(cell.itertext()) for cell in row])
        return root, rows


def test_export_permissions(employee):
    client, _, _ = employee
    assert client.get(URL).status_code == 403
    client.cookies.clear()
    assert client.get(URL).status_code == 401
    signin(client)
    _, rows = sheet(client.get(URL))
    assert len(rows) == 1
    assert rows[0] == ['Ngày', 'Tài khoản', 'Họ tên', 'Hình thức', 'Check-in', 'Kết thúc', 'Loại kết thúc']


def test_export_sessions_dates_filter_and_safe_text(employee, migrated_db):
    client, _, uid = employee
    migrated_db.execute("UPDATE geoattend.profiles SET full_name=%s,is_active=false WHERE id=%s", ('=SUM(1,2) <Nhân viên>', uid))
    day = migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,'2026-10-14','CHECKED_OUT') RETURNING id", (uid,)).fetchone()['id']
    migrated_db.execute("INSERT INTO geoattend.work_sessions(day_id,work_mode,start_time,end_time,end_source,start_reason) VALUES(%s,'OFFICE','2026-10-14 01:00+00','2026-10-14 05:00+00','USER','private reason'),(%s,'REMOTE','2026-10-14 06:00+00','2026-10-14 10:00+00','USER','private reason')", (day, day))
    migrated_db.execute("INSERT INTO geoattend.attendance_events(day_id,event_type,event_time,source) VALUES(%s,'LUNCH_START','2026-10-14 05:00+00','USER')", (day,))
    migrated_db.commit()
    signin(client)
    root, rows = sheet(client.get(URL, params={'from': '2026-10-14', 'to': '2026-10-14', 'user_id': uid}))
    assert len(rows) == 3
    assert rows[1][1:4] == ['worker', '=SUM(1,2) <Nhân viên>', 'Office']
    assert rows[2][3] == 'Remote'
    assert [r[6] for r in rows[1:]] == ['Nghỉ trưa', 'Check-out']
    # Native Excel dates/times, not strings: 2026-10-14, 08:00/12:00, 13:00/17:00 VN.
    assert [r[0] for r in rows[1:]] == ['46309', '46309']
    assert [float(rows[1][4]), float(rows[1][5])] == pytest.approx([8/24, 12/24])
    assert [float(rows[2][4]), float(rows[2][5])] == pytest.approx([13/24, 17/24])
    assert all(c.get('t') == 'inlineStr' for c in root.findall('s:sheetData/s:row', NS)[1].findall('s:c', NS)[1:4])
    assert 'private reason' not in str(rows) and 'GPS' not in str(rows)
    assert len(sheet(client.get(URL, params={'from': '2026-10-15', 'to': '2026-10-15'}))[1]) == 1


def test_export_leave_and_deleted_history(employee, migrated_db):
    from app.accounts.service import create_user
    client, headers, uid = employee
    assert action(client, headers, kind='MORNING_LEAVE', reason='private leave').status_code == 200
    assert action(client, headers, 1).status_code == 200
    other = create_user(migrated_db, 'other', 'Người khác', 'Worker1234')
    migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,'2026-10-14','FULL_DAY_LEAVE')", (other.id,))
    migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status,history_deleted) VALUES(%s,'2026-10-13','NOT_STARTED',true)", (uid,))
    migrated_db.commit()
    signin(client)
    _, rows = sheet(client.get(URL))
    assert len(rows) == 4
    assert {r[3] for r in rows[1:]} == {'Nghỉ buổi sáng', 'Remote', 'Nghỉ cả ngày'}
    assert any(r[6] == 'Đang làm việc' for r in rows[1:])
    assert all('private' not in value for r in rows for value in r)
    filtered = sheet(client.get(URL, params={'user_id': str(other.id)}))[1]
    assert len(filtered) == 2 and filtered[1][1] == 'other'


@pytest.mark.parametrize('params', [
    {'from': '2026-10-15', 'to': '2026-10-14'},
    {'from': '2025-01-01', 'to': '2026-10-14'},
    {'from': 'bad-date'}, {'user_id': 'bad-id'}, {'page': '1'}, {'to': '0001-01-01'},
])
def test_export_rejects_invalid_filters(employee, params):
    client, _, _ = employee
    signin(client)
    assert client.get(URL, params=params).status_code == 422


def test_export_unknown_user_and_admin_target(employee):
    client, _, _ = employee
    admin = signin(client).json()['id']
    assert client.get(URL, params={'user_id': str(uuid4())}).status_code == 404
    assert client.get(URL, params={'user_id': admin}).status_code == 404


def test_export_reconciles_system_end(employee, monkeypatch):
    client, headers, _ = employee
    assert action(client, headers).status_code == 200
    monkeypatch.setattr('app.clock.utc_now', lambda: datetime(2026, 10, 14, 13, tzinfo=timezone.utc))
    signin(client)
    _, rows = sheet(client.get(URL))
    assert rows[1][6] == 'Hệ thống tự đóng'
    assert float(rows[1][5]) == pytest.approx(20/24)


def test_export_rechecks_revoked_admin_session_after_wait(employee, test_dsn, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import psycopg
    from app.admin import export
    client, _, uid = employee
    admin_id = signin(client).json()['id']
    reached = Event()
    original = export.lock_profiles
    def marked(*args):
        reached.set()
        return original(*args)
    monkeypatch.setattr(export, 'lock_profiles', marked)
    with psycopg.connect(test_dsn) as blocker:
        blocker.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE', (uid,))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(client.get, URL)
            assert reached.wait(10)
            blocker.execute('UPDATE geoattend.auth_sessions SET revoked_at=now() WHERE user_id=%s', (admin_id,))
            blocker.commit()
            assert future.result(15).status_code == 401
