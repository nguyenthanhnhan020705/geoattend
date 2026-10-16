from uuid import UUID

import pytest
from tests.integration.test_attendance import employee, action

pytestmark=pytest.mark.integration


def test_equal_timestamp_timeline_preserves_state_and_replay(employee,migrated_db,record_property):
    client,headers,_=employee
    assert action(client,headers).status_code==200
    response=action(client,headers,1,'START_LUNCH',None)
    assert response.status_code==200
    # Force the known UUID tie-breaker in a closed session without changing time.
    # Requests reference event IDs: keep their references consistent as well.
    ids={row['event_type']:row['id'] for row in migrated_db.execute('SELECT id,event_type FROM geoattend.attendance_events')}
    for kind,new_id in [('LUNCH_START',UUID(int=1)),('WORK_END',UUID(int=2))]:
        migrated_db.execute('UPDATE geoattend.attendance_requests SET result_event_ids=array_replace(result_event_ids,%s,%s)',(ids[kind],new_id))
        migrated_db.execute('UPDATE geoattend.attendance_events SET id=%s WHERE id=%s',(new_id,ids[kind]))
    # All event_time/recorded_at values must tie to expose the presentation issue.
    migrated_db.execute("UPDATE geoattend.attendance_events SET recorded_at=event_time")
    migrated_db.commit()
    data=client.get('/api/attendance/history?from=2026-10-14&to=2026-10-14').json()['items'][0]
    types=[row['event_type'] for row in data['events']]
    record_property('uuid_tie_order',','.join(types))
    assert set(types)=={'WORK_START','WORK_END','LUNCH_START'}
    assert data['status']=='LUNCH_BREAK'
    assert len(data['sessions'])==1 and data['sessions'][0]['end_time'] is not None
    assert client.get('/api/attendance/status').json()['open_session'] is None
    assert action(client,headers,2,'START_REMOTE','Resume').status_code==200
    assert action(client,headers,3,'CHECK_OUT',None).status_code==200
    assert client.get('/api/attendance/status').json()['day_finished'] is True
