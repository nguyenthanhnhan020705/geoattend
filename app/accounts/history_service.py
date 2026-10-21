"""Admin access to employee history; profile locks serialize with attendance/worker."""
from app import clock
from app.errors import ApiError
from app.attendance.service import validate_session, reconcile_locked, read_history, WORKING


def lock_admin_target(conn, context, user_id):
    # Stable order also works when two admin requests target the same user.
    rows = conn.execute('SELECT id,role,is_active,username FROM geoattend.profiles WHERE id IN (%s,%s) ORDER BY id FOR UPDATE', (context.account.id,user_id)).fetchall()
    admin = next((r for r in rows if r['id'] == context.account.id),None)
    if not admin or not admin['is_active'] or admin['role'] != 'ADMIN':
        raise ApiError(403,'FORBIDDEN','Chức năng dành cho Admin.')
    validate_session(conn,context.account.id,context.session_id,clock.utc_now())
    target = next((r for r in rows if r['id'] == user_id),None)
    if target is None:
        raise ApiError(404,'USER_NOT_FOUND','Không tìm thấy nhân viên.')
    if target['role'] != 'USER':
        raise ApiError(403,'FORBIDDEN','Chỉ quản lý lịch sử của nhân viên.')
    return target


def history(conn, context, user_id, start, end, page, page_size):
    with conn.transaction():
        lock_admin_target(conn,context,user_id)
        now = clock.utc_now()
        reconcile_locked(conn,user_id,now)
        return read_history(conn,user_id,start,end,page,page_size,now)


def delete_day(conn, context, user_id, day_id, body):
    with conn.transaction():
        target = lock_admin_target(conn,context,user_id)
        if body.confirm_username != target['username']:
            raise ApiError(422,'CONFIRMATION_REQUIRED','Nhập đúng tên tài khoản nhân viên để xác nhận xóa vĩnh viễn.')
        day = conn.execute('SELECT * FROM geoattend.attendance_days WHERE id=%s AND user_id=%s FOR UPDATE',(day_id,user_id)).fetchone()
        if day is None:
            raise ApiError(404,'HISTORY_NOT_FOUND','Không tìm thấy ngày lịch sử của nhân viên.')
        if day['history_deleted'] and day['revision'] == body.expected_revision+1:
            return {'deleted':True,'work_date':day['work_date']}
        if day['revision'] != body.expected_revision:
            raise ApiError(409,'STALE_REVISION','Lịch sử đã thay đổi. Vui lòng tải lại trước khi xóa.')
        if day['status'] in (*WORKING,'LUNCH_BREAK') or conn.execute('SELECT id FROM geoattend.work_sessions WHERE day_id=%s AND end_time IS NULL',(day_id,)).fetchone():
            raise ApiError(409,'ACTIVE_DAY','Không thể xóa ngày đang làm việc hoặc nghỉ trưa. Nhân viên cần Check-out trước.')
        now = clock.utc_now()
        validate_session(conn,context.account.id,context.session_id,now)
        # Keep UUID/hash tombstones to reject old retries; clear all original results.
        # Older schema versions did not populate result_work_date; match their
        # original event/session references before removing those child rows.
        conn.execute('''UPDATE geoattend.attendance_requests
            SET history_deleted=true,completed_at=%s,result_event_ids=ARRAY[]::uuid[],
                result_session_id=NULL,result_status=NULL,result_revision=NULL,result_work_date=NULL
            WHERE user_id=%s AND (result_work_date=%s
                OR result_session_id IN (SELECT id FROM geoattend.work_sessions WHERE day_id=%s)
                OR result_event_ids && ARRAY(SELECT id FROM geoattend.attendance_events WHERE day_id=%s))''',
            (now,user_id,day['work_date'],day_id,day_id))
        conn.execute('DELETE FROM geoattend.office_locations WHERE session_id IN (SELECT id FROM geoattend.work_sessions WHERE day_id=%s)',(day_id,))
        conn.execute('DELETE FROM geoattend.attendance_events WHERE day_id=%s',(day_id,))
        conn.execute('DELETE FROM geoattend.work_sessions WHERE day_id=%s',(day_id,))
        # Minimal revision marker blocks stale tabs even when deleting today's history.
        conn.execute("UPDATE geoattend.attendance_days SET history_deleted=true,status='NOT_STARTED',revision=revision+1,updated_at=%s WHERE id=%s",(now,day_id))
        return {'deleted':True,'work_date':day['work_date']}
