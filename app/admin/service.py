"""Read one attendance projection while holding the writers' profile locks."""
from app import clock
from app.errors import ApiError
from app.attendance.service import validate_session, reconcile_locked, snapshot, VIETNAM
from app.admin.schemas import STATUSES


def lock_profiles(conn, context):
    # Same global UUID order as history deletion. Include inactive employees.
    profiles = conn.execute('SELECT id,username,full_name,role,is_active FROM geoattend.profiles ORDER BY id FOR UPDATE').fetchall()
    admin = next((row for row in profiles if row['id']==context.account.id),None)
    if not admin or not admin['is_active'] or admin['role']!='ADMIN':
        raise ApiError(403,'FORBIDDEN','Chức năng dành cho Admin.')
    return profiles


def build_snapshot(conn, context):
    with conn.transaction():
        profiles = lock_profiles(conn,context)
        now = clock.utc_now()
        validate_session(conn,context.account.id,context.session_id,now)
        items = []
        counts = dict.fromkeys(STATUSES,0)
        for profile in profiles:
            if profile['role']!='USER':
                continue
            reconcile_locked(conn,profile['id'],now)
            state = snapshot(conn,profile['id'],now)
            item = {key:profile[key] for key in ('id','username','full_name','is_active')}
            item.update(status=state['status'],open_session=state['open_session'])
            items.append(item)
            counts[item['status']] += 1
        return dict(as_of=now,work_date=now.astimezone(VIETNAM).date(),total_users=len(items),counts=counts,items=items,onsite=[])
