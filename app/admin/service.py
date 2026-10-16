"""Read one attendance projection while holding the writers' profile locks."""
from app import clock
from app.errors import ApiError
from app.attendance.service import validate_session, reconcile_locked, VIETNAM
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
        users=[profile for profile in profiles if profile['role']=='USER']
        user_ids={profile['id'] for profile in users}
        # All profiles are already locked in UUID order. Only overdue days need
        # reconciliation; ordinary reads must not issue several queries/User
        # while holding the writers' global lock set.
        overdue=conn.execute("""SELECT DISTINCT user_id FROM geoattend.attendance_days
            WHERE status IN ('WORKING_REMOTE','WORKING_OFFICE','LUNCH_BREAK')
            AND (work_date + time '20:00') AT TIME ZONE 'Asia/Ho_Chi_Minh' <= %s
            ORDER BY user_id""",(now,)).fetchall()
        for row in overdue:
            if row['user_id'] in user_ids:reconcile_locked(conn,row['user_id'],now)
        work_date=now.astimezone(VIETNAM).date()
        days={row['user_id']:row for row in conn.execute("""SELECT d.user_id,d.status,
            s.id AS session_id,s.work_mode,s.start_time,s.start_reason,
            EXISTS(SELECT 1 FROM geoattend.attendance_events e
                WHERE e.session_id=s.id AND e.event_type='WORK_START'
                AND e.location_verified=true) AS location_verified
            FROM geoattend.attendance_days d LEFT JOIN geoattend.work_sessions s
                ON s.day_id=d.id AND s.end_time IS NULL
            WHERE d.work_date=%s""",(work_date,)).fetchall()}
        items = []
        onsite = []
        counts = dict.fromkeys(STATUSES,0)
        for profile in users:
            day=days.get(profile['id'])
            opened=None
            if day and day['session_id']:
                opened=dict(id=day['session_id'],**{key:day[key] for key in ('work_mode','start_time','start_reason')})
            item = {key:profile[key] for key in ('id','username','full_name','is_active')}
            item.update(status=day['status'] if day else 'NOT_STARTED',open_session=opened)
            items.append(item)
            counts[item['status']] += 1
            opened = item['open_session']
            if item['status']=='WORKING_OFFICE' and opened and opened['work_mode']=='OFFICE':
                if day['location_verified']:
                    onsite.append(dict(**item,location_verified=True,location=get_location(conn,opened['id'],now)))
        return dict(as_of=now,work_date=work_date,total_users=len(items),counts=counts,items=items,onsite=onsite,office=get_office(conn))
