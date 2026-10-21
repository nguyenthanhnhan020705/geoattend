"""Admin-only attendance export. Read a consistent projection without GPS."""
from datetime import timedelta
from app import clock
from app.admin.service import lock_profiles
from app.attendance.service import VIETNAM, reconcile_locked, validate_session
from app.errors import ApiError
from app.admin.xlsx import attendance_workbook


def export_attendance(conn, context, start=None, end=None, user_id=None):
    with conn.transaction():
        profiles = lock_profiles(conn, context)
        now = clock.utc_now()
        validate_session(conn, context.account.id, context.session_id, now)
        end = end or now.astimezone(VIETNAM).date()
        try:
            start = start or end - timedelta(days=6)
        except OverflowError:
            raise ApiError(422, 'INVALID_RANGE', 'Chọn khoảng ngày hợp lệ, tối đa 366 ngày.')
        if start > end or (end-start).days >= 366:
            raise ApiError(422, 'INVALID_RANGE', 'Chọn khoảng ngày hợp lệ, tối đa 366 ngày.')
        users = [p for p in profiles if p['role'] == 'USER' and (user_id is None or p['id'] == user_id)]
        if user_id is not None and not users:
            raise ApiError(404, 'USER_NOT_FOUND', 'Không tìm thấy nhân viên.')
        user_ids = [p['id'] for p in users]
        overdue = conn.execute("""SELECT DISTINCT user_id FROM geoattend.attendance_days
            WHERE user_id=ANY(%s) AND status IN ('WORKING_REMOTE','WORKING_OFFICE','LUNCH_BREAK')
            AND (work_date + time '20:00') AT TIME ZONE 'Asia/Ho_Chi_Minh' <= %s
            ORDER BY user_id""", (user_ids, now)).fetchall()
        for row in overdue:
            reconcile_locked(conn, row['user_id'], now)
        # Never read GPS, reasons, auth data or request payloads into this projection.
        rows = conn.execute("""SELECT d.id AS day_id,d.work_date,p.username,p.full_name,
            s.id AS session_id,s.work_mode,s.start_time,s.end_time,s.end_source
            FROM geoattend.attendance_days d JOIN geoattend.profiles p ON p.id=d.user_id
            JOIN geoattend.work_sessions s ON s.day_id=d.id
            WHERE d.user_id=ANY(%s) AND d.work_date BETWEEN %s AND %s AND NOT d.history_deleted
            ORDER BY d.work_date,p.full_name,p.username,s.start_time,s.id""", (user_ids, start, end)).fetchall()
        events = conn.execute("""SELECT d.id AS day_id,d.work_date,p.username,p.full_name,
            e.event_type,e.event_time FROM geoattend.attendance_days d
            JOIN geoattend.profiles p ON p.id=d.user_id
            JOIN geoattend.attendance_events e ON e.day_id=d.id
            WHERE d.user_id=ANY(%s) AND d.work_date BETWEEN %s AND %s AND NOT d.history_deleted
            AND e.event_type IN ('LUNCH_START','MORNING_LEAVE','FULL_DAY_LEAVE')
            ORDER BY e.event_time,e.recorded_at,e.id""", (user_ids, start, end)).fetchall()
        lunches = [(e['day_id'], e['event_time']) for e in events if e['event_type'] == 'LUNCH_START']
        starts = {}
        for row in rows:
            starts.setdefault((row['day_id'], row['start_time']), set()).add(row['session_id'])
        output = []
        for row in rows:
            key = (row['day_id'], row['end_time'])
            if row['end_time'] is None:
                ending = 'Đang làm việc'
            elif row['end_source'] == 'SYSTEM':
                ending = 'Hệ thống tự đóng'
            elif key in lunches:
                ending = 'Nghỉ trưa'
                lunches.remove(key)
            elif starts.get(key, set()) - {row['session_id']}:
                ending = 'Chuyển hình thức'
            else:
                ending = 'Check-out'
            output.append((row['work_date'], row['username'], row['full_name'],
                           'Office' if row['work_mode'] == 'OFFICE' else 'Remote',
                           row['start_time'], row['end_time'], ending))
        # Full-day leave may also exist in imported/setup data without an event.
        leaves = conn.execute("""SELECT d.work_date,p.username,p.full_name,d.status
            FROM geoattend.attendance_days d JOIN geoattend.profiles p ON p.id=d.user_id
            WHERE d.user_id=ANY(%s) AND d.work_date BETWEEN %s AND %s AND NOT d.history_deleted
            AND d.status IN ('MORNING_LEAVE','FULL_DAY_LEAVE')""", (user_ids, start, end)).fetchall()
        leave_keys = set()
        for event in events:
            if event['event_type'] not in ('MORNING_LEAVE','FULL_DAY_LEAVE'):
                continue
            kind = 'Nghỉ buổi sáng' if event['event_type'] == 'MORNING_LEAVE' else 'Nghỉ cả ngày'
            output.append((event['work_date'], event['username'], event['full_name'], kind, None, None, ''))
            leave_keys.add((event['work_date'], event['username'], event['event_type']))
        for row in leaves:
            if (row['work_date'], row['username'], row['status']) not in leave_keys:
                kind = 'Nghỉ buổi sáng' if row['status'] == 'MORNING_LEAVE' else 'Nghỉ cả ngày'
                output.append((row['work_date'], row['username'], row['full_name'], kind, None, None, ''))
        output.sort(key=lambda row: (row[0], row[2], row[1], row[4].timestamp() if row[4] else float('-inf')))
        validate_session(conn, context.account.id, context.session_id, clock.utc_now())
    return attendance_workbook(output), f'geoattend_{start}_{end}.xlsx'
