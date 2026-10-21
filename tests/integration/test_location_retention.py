from datetime import datetime,timezone,timedelta
from uuid import uuid4
import pytest
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.conninfo import make_conninfo
from tests.integration.test_office_attendance import configured,office_action
from tests.integration.test_attendance import employee

pytestmark=pytest.mark.integration


def test_expiry_hidden_before_worker_and_purge_keeps_history(configured,migrated_db,monkeypatch):
    from app.gis.retention import purge_locations
    client,headers,_=configured
    key=str(uuid4()); first=office_action(client,headers,request_id=key)
    assert first.status_code==200
    expiry=datetime(2026,11,13,2,tzinfo=timezone.utc)
    migrated_db.execute('UPDATE geoattend.auth_sessions SET expires_at=%s',(expiry+timedelta(days=1),));migrated_db.commit()
    def history_location():
        data=client.get('/api/attendance/history?from=2026-10-14&to=2026-10-14').json()
        return data['items'][0]['sessions'][0]['location']
    monkeypatch.setattr('app.clock.utc_now',lambda:expiry-timedelta(microseconds=1))
    available=history_location()
    assert available['status']=='available' and available['longitude']==106.5 and available['accuracy_m']==15
    monkeypatch.setattr('app.clock.utc_now',lambda:expiry)
    expired=history_location()
    assert expired['status']=='expired' and 'longitude' not in expired and 'accuracy_m' not in expired
    # Renew only test login session expiry so this historical replay can be
    # authenticated at the controlled clock; business rows remain untouched.
    migrated_db.execute('UPDATE geoattend.auth_sessions SET expires_at=%s',(expiry+timedelta(days=1),));migrated_db.commit()
    replay=office_action(client,headers,request_id=key)
    assert replay.status_code==200 and replay.json()==first.json()
    assert 'longitude' not in replay.text
    assert migrated_db.execute('SELECT point IS NOT NULL AS retained FROM geoattend.office_locations').fetchone()['retained']
    assert purge_locations(migrated_db,expiry)==1
    assert purge_locations(migrated_db,expiry)==0
    row=migrated_db.execute('SELECT point,accuracy_m,purged_at FROM geoattend.office_locations').fetchone()
    assert row['point'] is None and row['accuracy_m'] is None and row['purged_at']==expiry
    assert migrated_db.execute('SELECT location_verified FROM geoattend.attendance_events WHERE event_type=\'WORK_START\'').fetchone()['location_verified'] is True
    assert history_location()['status']=='expired'


def test_runtime_can_purge_expired_locations(configured,migrated_db,test_dsn):
    from app.gis.retention import purge_locations
    from app.db.migrations import grant_runtime
    client,headers,_=configured
    assert office_action(client,headers).status_code==200
    migrated_db.execute("UPDATE geoattend.office_locations SET expires_at=recorded_at")
    role='gps_runtime_'+uuid4().hex
    migrated_db.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    grant_runtime(migrated_db,role); migrated_db.commit()
    try:
        with psycopg.connect(make_conninfo(test_dsn,user=role),row_factory=dict_row) as conn:
            assert purge_locations(conn,datetime(2026,10,14,2,tzinfo=timezone.utc))==1
    finally:
        migrated_db.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
        migrated_db.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)));migrated_db.commit()
