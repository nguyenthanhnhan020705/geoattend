"""Profile lock is always acquired before day/session locks, including maintenance."""
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
from app import clock
from app.errors import ApiError

VIETNAM = timezone(timedelta(hours=7))
WORKING = ('WORKING_REMOTE', 'WORKING_OFFICE')


def cutoff(work_date):
    return datetime.combine(work_date, time(20), VIETNAM)


def lock_user(conn, user_id):
    row = conn.execute('SELECT role,is_active FROM geoattend.profiles WHERE id=%s FOR UPDATE', (user_id,)).fetchone()
    if row is None or not row['is_active']:
        raise ApiError(401, 'AUTH_REQUIRED', 'Phiên đăng nhập không còn hợp lệ.')
    if row['role'] != 'USER':
        raise ApiError(403, 'FORBIDDEN', 'Chức năng chấm công dành cho User.')


def validate_session(conn,user_id,session_id,now):
    if session_id is not None and not conn.execute('SELECT id FROM geoattend.auth_sessions WHERE id=%s AND user_id=%s AND revoked_at IS NULL AND expires_at>%s',(session_id,user_id,now)).fetchone():
        raise ApiError(401,'AUTH_REQUIRED','Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.')


def event(conn, day_id, session_id, kind, moment, recorded, source, reason=None):
    return conn.execute('INSERT INTO geoattend.attendance_events(day_id,session_id,event_type,event_time,recorded_at,source,reason) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id', (day_id,session_id,kind,moment,recorded,source,reason)).fetchone()['id']


def reconcile_locked(conn, user_id, now):
    rows = conn.execute("SELECT * FROM geoattend.attendance_days WHERE user_id=%s AND status IN ('WORKING_REMOTE','WORKING_OFFICE','LUNCH_BREAK') ORDER BY work_date FOR UPDATE", (user_id,)).fetchall()
    closed = 0
    for day in rows:
        deadline = cutoff(day['work_date'])
        if now < deadline:
            continue
        if day['status'] in WORKING:
            session = conn.execute("UPDATE geoattend.work_sessions SET end_time=%s,end_source='SYSTEM' WHERE day_id=%s AND end_time IS NULL RETURNING id", (deadline,day['id'])).fetchone()
            if session is None:
                raise ApiError(503,'INCONSISTENT_ATTENDANCE','Dữ liệu phiên cần được kiểm tra.')
            event(conn,day['id'],session['id'],'WORK_END',deadline,now,'SYSTEM')
        else:
            event(conn,day['id'],None,'DAY_END',deadline,now,'SYSTEM')
        conn.execute("UPDATE geoattend.attendance_days SET status='CHECKED_OUT',revision=revision+1,updated_at=%s WHERE id=%s", (now,day['id']))
        closed += 1
    return closed


def current_day(conn, user_id, work_date):
    return conn.execute('SELECT * FROM geoattend.attendance_days WHERE user_id=%s AND work_date=%s', (user_id,work_date)).fetchone()


def snapshot(conn, user_id, now):
    work_date = now.astimezone(VIETNAM).date()
    day = current_day(conn,user_id,work_date)
    state = day['status'] if day else 'NOT_STARTED'
    opened = None
    if day:
        opened = conn.execute('SELECT id,work_mode,start_time,start_reason FROM geoattend.work_sessions WHERE day_id=%s AND end_time IS NULL', (day['id'],)).fetchone()
    allowed = []
    if now < cutoff(work_date):
        if state in ('NOT_STARTED','CHECKED_OUT'):
            allowed = ['START_OFFICE','START_REMOTE']
        elif state in WORKING:
            allowed = ['CHECK_OUT']
    return dict(work_date=work_date,status=state,revision=day['revision'] if day else 0,open_session=opened,server_time=now,allowed_actions=allowed)


def status(conn, user_id, session_id=None):
    with conn.transaction():
        lock_user(conn,user_id)
        now = clock.utc_now()
        validate_session(conn,user_id,session_id,now)
        reconcile_locked(conn,user_id,now)
        return snapshot(conn,user_id,now)


def result(row):
    return dict(event_ids=[str(i) for i in row['result_event_ids']], session_id=str(row['result_session_id']) if row['result_session_id'] else None, work_date=row['result_work_date'],status=row['result_status'],revision=row['result_revision'])


def act(conn, user_id, body, session_id=None):
    from app.gis.service import verify_office,store_location
    excluded={'request_id'}
    if body.action!='START_OFFICE':
        excluded.update({'latitude','longitude','accuracy_m'})
    payload = body.model_dump(mode='json', exclude=excluded)
    digest = hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    failure = None
    answer = None
    # Raise expected conflicts only AFTER the transaction commits catch-up.
    # A database failure still rolls back the entire attempted action.
    with conn.transaction():
        lock_user(conn,user_id)
        now = clock.utc_now()
        validate_session(conn,user_id,session_id,now)
        reconcile_locked(conn,user_id,now)
        previous = conn.execute('SELECT * FROM geoattend.attendance_requests WHERE user_id=%s AND request_id=%s', (user_id,body.request_id)).fetchone()
        if previous:
            if previous['payload_hash'] != digest:
                failure = ApiError(409,'REQUEST_CONFLICT','Mã thao tác đã được dùng với nội dung khác.')
            else:
                answer = result(previous)
        else:
            now = clock.utc_now()  # Recheck after lock/queries immediately before writes.
            validate_session(conn,user_id,session_id,now)
            reconcile_locked(conn,user_id,now)
            today = now.astimezone(VIETNAM).date()
            day = current_day(conn,user_id,today)
            state = day['status'] if day else 'NOT_STARTED'
            revision = day['revision'] if day else 0
            if body.expected_work_date != today:
                failure = ApiError(409,'STALE_DATE','Ngày làm việc đã thay đổi. Vui lòng tải lại và thực hiện thao tác mới.')
            elif now >= cutoff(today):
                failure = ApiError(409,'DAY_CLOSED','Ngày làm việc đã kết thúc lúc 20:00 giờ Việt Nam.')
            elif revision != body.expected_revision:
                failure = ApiError(409,'STALE_REVISION','Trạng thái đã thay đổi. Vui lòng tải lại.')
            elif (body.action in ('START_REMOTE','START_OFFICE') and state not in ('NOT_STARTED','CHECKED_OUT')) or (body.action=='CHECK_OUT' and state not in WORKING):
                failure = ApiError(409,'INVALID_TRANSITION','Không thể thực hiện thao tác ở trạng thái hiện tại.')
            else:
                office=None
                if body.action=='START_OFFICE':
                    try:
                        office=verify_office(conn,body.latitude,body.longitude)
                    except ApiError as error:
                        failure=error
                    # Acquiring the office lock/GIS verification may have
                    # waited across cutoff, midnight or session revocation.
                    now=clock.utc_now()
                    validate_session(conn,user_id,session_id,now)
                    reconcile_locked(conn,user_id,now)
                    if now.astimezone(VIETNAM).date()!=today:
                        failure=ApiError(409,'STALE_DATE','Ngày làm việc đã thay đổi. Vui lòng tải lại.')
                    elif now>=cutoff(today):
                        failure=ApiError(409,'DAY_CLOSED','Ngày làm việc đã kết thúc lúc 20:00 giờ Việt Nam.')
                if failure is None and day is None:
                    day = conn.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,%s,'NOT_STARTED') RETURNING *", (user_id,today)).fetchone()
                if failure is None and body.action in ('START_REMOTE','START_OFFICE'):
                    mode='OFFICE' if office else 'REMOTE'
                    session_id = conn.execute('INSERT INTO geoattend.work_sessions(day_id,work_mode,start_time,start_reason,office_revision) VALUES(%s,%s,%s,%s,%s) RETURNING id', (day['id'],mode,now,body.reason,office['revision'] if office else None)).fetchone()['id']
                    event_id = event(conn,day['id'],session_id,'WORK_START',now,now,'USER',body.reason)
                    if office:
                        conn.execute('UPDATE geoattend.attendance_events SET location_verified=true WHERE id=%s',(event_id,))
                        store_location(conn,session_id,event_id,body,now)
                    state = 'WORKING_'+mode
                elif failure is None:
                    session = conn.execute("UPDATE geoattend.work_sessions SET end_time=%s,end_source='USER',end_reason=%s WHERE day_id=%s AND end_time IS NULL RETURNING id", (now,body.reason,day['id'])).fetchone()
                    if session is None:
                        raise ApiError(503,'INCONSISTENT_ATTENDANCE','Dữ liệu phiên cần được kiểm tra.')
                    session_id = session['id']
                    event_id = event(conn,day['id'],session_id,'WORK_END',now,now,'USER',body.reason)
                    state = 'CHECKED_OUT'
                if failure is None:
                    conn.execute('UPDATE geoattend.attendance_days SET status=%s,revision=revision+1,updated_at=%s WHERE id=%s', (state,now,day['id']))
                    saved = conn.execute('INSERT INTO geoattend.attendance_requests(user_id,request_id,payload_hash,result_event_ids,completed_at,result_status,result_revision,result_work_date,result_session_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *', (user_id,body.request_id,digest,[event_id],now,state,revision+1,today,session_id)).fetchone()
                    answer = result(saved)
    if failure:
        raise failure
    return answer


def history(conn, user_id, start, end, page, page_size, session_id=None):
    from app.gis.service import get_location
    with conn.transaction():
        lock_user(conn,user_id)
        now = clock.utc_now()
        validate_session(conn,user_id,session_id,now)
        reconcile_locked(conn,user_id,now)
        end = end or now.astimezone(VIETNAM).date()
        start = start or end-timedelta(days=6)
        if start > end:
            raise ApiError(422,'INVALID_RANGE','Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.')
        total = conn.execute('SELECT count(*) AS n FROM geoattend.attendance_days WHERE user_id=%s AND work_date BETWEEN %s AND %s', (user_id,start,end)).fetchone()['n']
        days = conn.execute('SELECT id,work_date,status,revision FROM geoattend.attendance_days WHERE user_id=%s AND work_date BETWEEN %s AND %s ORDER BY work_date DESC LIMIT %s OFFSET %s', (user_id,start,end,page_size,(page-1)*page_size)).fetchall()
        for day in days:
            day['sessions'] = conn.execute('SELECT id,work_mode,start_time,end_time,start_reason,end_reason,end_source FROM geoattend.work_sessions WHERE day_id=%s ORDER BY start_time,id', (day['id'],)).fetchall()
            for session in day['sessions']:
                session['location']=get_location(conn,session['id'],now) if session['work_mode']=='OFFICE' else None
            day['events'] = conn.execute('SELECT id,session_id,event_type,event_time,recorded_at,source,reason,location_verified FROM geoattend.attendance_events WHERE day_id=%s ORDER BY event_time,recorded_at,id', (day['id'],)).fetchall()
        return dict(items=days,total=total,page=page,page_size=page_size)


def maintain(conn):
    with conn.transaction():
        now = clock.utc_now()
        # SQL narrows candidates; authoritative clock/cutoff is rechecked
        # under the same profile lock as actions. Includes overdue old days.
        users = conn.execute("SELECT DISTINCT user_id FROM geoattend.attendance_days WHERE status IN ('WORKING_REMOTE','WORKING_OFFICE','LUNCH_BREAK') AND (work_date + time '20:00') AT TIME ZONE 'Asia/Ho_Chi_Minh' <= %s ORDER BY user_id", (now,)).fetchall()
    closed = 0
    for row in users:
        with conn.transaction():
            # Inactive users still need their existing days closed.
            conn.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE', (row['user_id'],)).fetchone()
            closed += reconcile_locked(conn,row['user_id'],clock.utc_now())
    return closed
