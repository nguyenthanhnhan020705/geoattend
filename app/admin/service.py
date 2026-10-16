"""Read one attendance projection while holding the writers' profile locks."""
from app import clock
from app.errors import ApiError
from app.attendance.service import validate_session, reconcile_locked, snapshot, VIETNAM
from app.admin.schemas import STATUSES
from app.gis.service import get_location, get_office


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
        onsite = []
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
            opened = item['open_session']
            if item['status']=='WORKING_OFFICE' and opened and opened['work_mode']=='OFFICE':
                verified = conn.execute("SELECT location_verified FROM geoattend.attendance_events WHERE session_id=%s AND event_type='WORK_START'",(opened['id'],)).fetchone()
                if verified and verified['location_verified']:
                    onsite.append(dict(**item,location_verified=True,location=get_location(conn,opened['id'],now)))
        return dict(as_of=now,work_date=now.astimezone(VIETNAM).date(),total_users=len(items),counts=counts,items=items,onsite=onsite,office=get_office(conn))
