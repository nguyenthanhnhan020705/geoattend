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
        # Read only attendance fields needed by this Admin report, never GPS or auth payloads.
        params = (user_ids, start, end)
        days = conn.execute("""SELECT d.id AS day_id,d.work_date,d.status,p.username,p.full_name
            FROM geoattend.attendance_days d JOIN geoattend.profiles p ON p.id=d.user_id
            WHERE d.user_id=ANY(%s) AND d.work_date BETWEEN %s AND %s AND NOT d.history_deleted
            ORDER BY d.work_date,p.full_name,p.username""", params).fetchall()
        sessions = conn.execute("""SELECT s.day_id,s.work_mode,s.start_time,s.end_time,s.end_source,
            CASE WHEN s.work_mode='REMOTE' THEN s.start_reason END AS reason
            FROM geoattend.work_sessions s JOIN geoattend.attendance_days d ON d.id=s.day_id
            WHERE d.user_id=ANY(%s) AND d.work_date BETWEEN %s AND %s AND NOT d.history_deleted
            ORDER BY s.start_time,s.id""", params).fetchall()
        events = conn.execute("""SELECT e.day_id,e.event_type,e.event_time,
            CASE WHEN e.event_type IN ('MORNING_LEAVE','FULL_DAY_LEAVE') THEN e.reason END AS reason
            FROM geoattend.attendance_events e JOIN geoattend.attendance_days d ON d.id=e.day_id
            WHERE d.user_id=ANY(%s) AND d.work_date BETWEEN %s AND %s AND NOT d.history_deleted
            AND e.event_type IN ('LUNCH_START','MORNING_LEAVE','FULL_DAY_LEAVE')
            ORDER BY e.event_time,e.recorded_at,e.id""", params).fetchall()
        output = daily_rows(days, sessions, events)
        validate_session(conn, context.account.id, context.session_id, clock.utc_now())
    return attendance_workbook(output), f'geoattend_{start}_{end}.xlsx'


def daily_rows(days, sessions, events):
    """One row per employee-day; missing times are never inferred as attendance."""
    grouped_sessions, grouped_events = {}, {}
    for session in sessions:
        grouped_sessions.setdefault(session['day_id'], []).append(session)
    for event in events:
        grouped_events.setdefault(event['day_id'], []).append(event)
    output = []
    leave_labels = {'MORNING_LEAVE': 'Nghỉ buổi sáng', 'FULL_DAY_LEAVE': 'Nghỉ cả ngày'}
    for day in days:
        work = sorted(grouped_sessions.get(day['day_id'], []), key=lambda row: row['start_time'])
        day_events = grouped_events.get(day['day_id'], [])
        leave = [e for e in day_events if e['event_type'] in leave_labels]
        if not work and not leave and day['status'] not in leave_labels:
            continue
        modes, reasons = [], []
        def add(values, value):
            if value and value not in values:
                values.append(value)
        for event in leave:
            label = leave_labels[event['event_type']]
            add(modes, label)
            if event['reason']:
                add(reasons, label + ': ' + event['reason'])
        if day['status'] in leave_labels:
            add(modes, leave_labels[day['status']])
        lunches = [e['event_time'] for e in day_events if e['event_type'] == 'LUNCH_START']
        lunch = min(lunches) if lunches else None
        morning_leave = any(e['event_type'] == 'MORNING_LEAVE' for e in leave) or day['status'] == 'MORNING_LEAVE'
        morning = afternoon = checkout = None
        for session in work:
            add(modes, 'Office' if session['work_mode'] == 'OFFICE' else 'Remote')
            if session['work_mode'] == 'REMOTE' and session['reason']:
                add(reasons, 'Remote: ' + session['reason'])
            started = session['start_time']
            is_afternoon = morning_leave or (started >= lunch if lunch else started.astimezone(VIETNAM).hour >= 12)
            if is_afternoon:
                afternoon = afternoon or started
            else:
                morning = morning or started
        if work:
            last = work[-1]
            if last['end_time'] and last['end_time'] not in lunches:
                checkout = last['end_time']
                if last['end_source'] == 'SYSTEM':
                    checkout = checkout.astimezone(VIETNAM).strftime('%H:%M:%S') + ' (hệ thống tự đóng)'
        output.append((day['work_date'], day['full_name'], ' / '.join(modes),
                       morning, lunch, afternoon, checkout, '\n'.join(reasons)))
    return output
