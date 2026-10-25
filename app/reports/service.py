"""Private PDF data; profile locks precede report locks, never attendance writes."""
from datetime import timedelta
import hashlib
import json
from app import clock
from app.errors import ApiError
from app.attendance.service import validate_session
from app.reports.policy import (
    VIETNAM, MAX_PDF_BYTES, SUNDAY_REMINDER, OVERDUE_REMINDER,
    week_start_for, week_deadline, first_required_week, validate_week,
)

META = 'id,user_id,week_start,filename,size_bytes,first_submitted_at,submitted_at,revision'


def metadata(row):
    if row is None:
        return None
    data = {key: row[key] for key in META.split(',')}
    data['week_end'] = row['week_start'] + timedelta(days=6)
    return data


def authorize(conn, context, admin=False):
    profile = conn.execute('SELECT id,role,is_active,created_at FROM geoattend.profiles WHERE id=%s FOR UPDATE',
                           (context.account.id,)).fetchone()
    if not profile or not profile['is_active']:
        raise ApiError(401, 'AUTH_REQUIRED', 'Phiên đăng nhập không còn hợp lệ.')
    if profile['role'] != ('ADMIN' if admin else 'USER'):
        raise ApiError(403, 'FORBIDDEN', 'Bạn không có quyền thực hiện thao tác báo cáo này.')
    validate_session(conn, profile['id'], context.session_id, clock.utc_now())
    return profile


def enabled_at(conn):
    row = conn.execute("SELECT applied_at FROM geoattend.schema_migrations WHERE name='005_weekly_reports.sql'").fetchone()
    if not row:
        raise ApiError(503, 'REPORTS_UNAVAILABLE', 'Chức năng báo cáo tuần chưa sẵn sàng.')
    return row['applied_at']


def status(conn, context):
    with conn.transaction():
        profile = authorize(conn, context)
        now = clock.utc_now()
        week = week_start_for(now)
        first = first_required_week(profile['created_at'], enabled_at(conn))
        rows = conn.execute(f'SELECT {META} FROM geoattend.weekly_reports WHERE user_id=%s AND week_start IN (%s,%s)',
                            (profile['id'], week, week-timedelta(days=7))).fetchall()
        reports = {row['week_start']: row for row in rows}
        notices = []
        if now.astimezone(VIETNAM).weekday() == 6 and week >= first and week not in reports:
            notices.append(dict(code='SUNDAY_DUE', message=SUNDAY_REMINDER, week_start=week, week_end=week+timedelta(days=6)))
        previous = week-timedelta(days=7)
        if previous >= first and previous not in reports:
            notices.append(dict(code='PREVIOUS_WEEK_MISSING', message=OVERDUE_REMINDER,
                                week_start=previous, week_end=previous+timedelta(days=6)))
        return dict(server_time=now, week_start=week, week_end=week+timedelta(days=6),
                    deadline=week_deadline(week), max_bytes=MAX_PDF_BYTES,
                    report=metadata(reports.get(week)), notices=notices)


def list_own(conn, context, page, page_size):
    with conn.transaction():
        authorize(conn, context)
        total = conn.execute('SELECT count(*) AS n FROM geoattend.weekly_reports WHERE user_id=%s',
                             (context.account.id,)).fetchone()['n']
        rows = conn.execute(f'SELECT {META} FROM geoattend.weekly_reports WHERE user_id=%s ORDER BY week_start DESC LIMIT %s OFFSET %s',
                            (context.account.id, page_size, (page-1)*page_size)).fetchall()
        return dict(items=[metadata(row) for row in rows], total=total, page=page, page_size=page_size)


def submit(conn, context, week_start, request_id, expected_revision, filename, content):
    validate_week(week_start)
    content_hash = hashlib.sha256(content).hexdigest()
    digest = hashlib.sha256(json.dumps([str(week_start), expected_revision, filename, content_hash],
                                      ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    with conn.transaction():
        profile = authorize(conn, context)
        row = conn.execute('SELECT '+META+',request_id,request_hash FROM geoattend.weekly_reports WHERE user_id=%s AND week_start=%s FOR UPDATE',
                           (profile['id'], week_start)).fetchone()
        if row and row['request_id'] == request_id:
            if row['request_hash'] != digest:
                raise ApiError(409, 'REQUEST_CONFLICT', 'Mã gửi báo cáo đã được dùng với nội dung khác.')
            return metadata(row)
        now = clock.utc_now()
        validate_session(conn, profile['id'], context.session_id, now)
        current = week_start_for(now)
        if week_start < current:
            raise ApiError(409, 'REPORT_WEEK_CLOSED', 'Tuần báo cáo đã hết hạn, không thể nộp hoặc thay thế.')
        if week_start > current:
            raise ApiError(409, 'FUTURE_WEEK', 'Chỉ được nộp báo cáo cho tuần hiện tại.')
        if week_start < first_required_week(profile['created_at'], enabled_at(conn)):
            raise ApiError(409, 'REPORT_WEEK_CLOSED', 'Tuần báo cáo chưa áp dụng cho tài khoản này.')
        revision = row['revision'] if row else 0
        if expected_revision != revision:
            raise ApiError(409, 'STALE_REVISION', 'Báo cáo đã thay đổi. Vui lòng tải lại trước khi nộp.')
        # An activation query can wait too: time/session at the actual write is authoritative.
        now = clock.utc_now()
        validate_session(conn, profile['id'], context.session_id, now)
        if week_start_for(now) != week_start:
            raise ApiError(409, 'REPORT_WEEK_CLOSED', 'Tuần báo cáo đã hết hạn, không thể nộp hoặc thay thế.')
        values = (filename, content, len(content), content_hash, now, revision+1, request_id, digest)
        if row:
            saved = conn.execute('UPDATE geoattend.weekly_reports SET filename=%s,pdf=%s,size_bytes=%s,content_sha256=%s,submitted_at=%s,revision=%s,request_id=%s,request_hash=%s WHERE id=%s RETURNING '+META,
                                 (*values, row['id'])).fetchone()
        else:
            saved = conn.execute('INSERT INTO geoattend.weekly_reports(filename,pdf,size_bytes,content_sha256,submitted_at,revision,request_id,request_hash,user_id,week_start,first_submitted_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING '+META,
                                 (*values, profile['id'], week_start, now)).fetchone()
        return metadata(saved)


def list_admin(conn, context, week_start, user_id, page, page_size):
    with conn.transaction():
        authorize(conn, context, admin=True)
        now = clock.utc_now()
        week = week_start or week_start_for(now)
        validate_week(week)
        activation = enabled_at(conn)
        where = "role='USER'" + (' AND id=%s' if user_id else '')
        args = (user_id,) if user_id else ()
        total = conn.execute('SELECT count(*) AS n FROM geoattend.profiles WHERE '+where, args).fetchone()['n']
        users = conn.execute('SELECT id,username,full_name,is_active,created_at FROM geoattend.profiles WHERE '+where+' ORDER BY full_name,username LIMIT %s OFFSET %s',
                             (*args, page_size, (page-1)*page_size)).fetchall()
        rows = conn.execute('SELECT '+META+' FROM geoattend.weekly_reports WHERE week_start=%s AND user_id=ANY(%s)',
                            (week, [user['id'] for user in users])).fetchall()
        reports = {row['user_id']: row for row in rows}
        items = []
        for user in users:
            report = reports.get(user['id'])
            state = 'SUBMITTED' if report else ('NOT_APPLICABLE' if week < first_required_week(user['created_at'], activation)
                    else 'OVERDUE' if now >= week_deadline(week) else 'PENDING')
            items.append({**{key:user[key] for key in ('id','username','full_name','is_active')},
                          'status':state, 'report':metadata(report)})
        return dict(week_start=week, week_end=week+timedelta(days=6), items=items, total=total, page=page, page_size=page_size)


def read_file(conn, context, report_id, admin=False, expected_revision=None):
    with conn.transaction():
        authorize(conn, context, admin=admin)
        row = conn.execute("SELECT r.filename,r.pdf,r.revision FROM geoattend.weekly_reports r JOIN geoattend.profiles p ON p.id=r.user_id WHERE r.id=%s AND p.role='USER'"+
                           ('' if admin else ' AND r.user_id=%s'),
                           (report_id,) if admin else (report_id, context.account.id)).fetchone()
        if not row:
            raise ApiError(404, 'REPORT_NOT_FOUND', 'Không tìm thấy báo cáo.')
        if expected_revision is not None and row['revision'] != expected_revision:
            raise ApiError(409,'STALE_REVISION','PDF đã được thay thế. Vui lòng tải lại danh sách báo cáo.')
        return row
