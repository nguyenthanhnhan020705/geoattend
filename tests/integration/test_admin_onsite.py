from datetime import datetime, timedelta, timezone
import pytest
from tests.integration.test_attendance import employee, action
from tests.integration.test_office_attendance import configured, office_action
from tests.test_auth_api import signin

pytestmark=pytest.mark.integration


def onsite(client):
    response=client.get('/api/admin/onsite')
    assert response.status_code==200
    return response.json()


def test_onsite_current_verified_session_and_resume(configured):
    client,headers,uid=configured
    first=office_action(client,headers).json()
    signin(client)
    data=onsite(client)
    assert data['items'][0]['id']==uid
    assert data['items'][0]['open_session']['id']==first['session_id']
    assert data['items'][0]['location_verified'] is True
    assert data['items'][0]['location']['latitude']==10.5
    assert data['office']['geom']['type']=='Polygon'
    assert client.get('/api/admin/dashboard').json()['onsite']==data['items']
    headers={'X-CSRF-Token':signin(client,'worker','Worker1234').json()['csrf_token']}
    assert action(client,headers,1,'START_LUNCH',None).status_code==200
    signin(client)
    assert onsite(client)['items']==[]
    headers={'X-CSRF-Token':signin(client,'worker','Worker1234').json()['csrf_token']}
    second=office_action(client,headers,2,latitude=10.6,longitude=106.6).json()
    signin(client)
    row=onsite(client)['items'][0]
    assert row['open_session']['id']==second['session_id']!=first['session_id']
    assert row['location']['latitude']==10.6
    headers={'X-CSRF-Token':signin(client,'worker','Worker1234').json()['csrf_token']}
    assert action(client,headers,3,'SWITCH_REMOTE','Nhà').status_code==200
    signin(client)
    assert onsite(client)['items']==[]


@pytest.mark.parametrize('delta,status',[(-1,'available'),(0,'expired'),(1,'expired')])
def test_onsite_gps_retention_before_purge(configured,migrated_db,delta,status):
    client,headers,_=configured
    office_action(client,headers)
    # Keep a current open session, independently age its GPS acquisition.
    expiry=datetime(2026,10,14,2,tzinfo=timezone.utc)-timedelta(seconds=delta)
    migrated_db.execute('UPDATE geoattend.office_locations SET recorded_at=%s,expires_at=%s',(expiry-timedelta(days=30),expiry))
    migrated_db.commit()
    signin(client)
    data=onsite(client)['items'][0]
    assert data['location_verified'] is True
    assert data['location']['status']==status
    if status=='expired':
        assert set(data['location'])=={'status','expires_at'}
        dashboard=client.get('/api/admin/dashboard').json()
        assert dashboard['onsite'][0]['location']==data['location']
    else:
        assert data['location']['longitude']==106.5 and data['location']['accuracy_m']==15
    assert migrated_db.execute('SELECT point IS NOT NULL AS retained FROM geoattend.office_locations').fetchone()['retained']


def test_onsite_missing_location_and_verification(configured,migrated_db):
    client,headers,_=configured
    office_action(client,headers)
    migrated_db.execute('DELETE FROM geoattend.office_locations'); migrated_db.commit()
    signin(client)
    row=onsite(client)['items'][0]
    assert row['location'] is None and row['location_verified'] is True
    migrated_db.execute('UPDATE geoattend.attendance_events SET location_verified=false'); migrated_db.commit()
    assert onsite(client)['items']==[]


def test_onsite_permissions_unconfigured_and_checkout(employee):
    client,_,_=employee
    assert client.get('/api/admin/onsite').status_code==403
    signin(client)
    data=onsite(client)
    assert data['items']==[] and data['office']['geom'] is None
    client.cookies.clear()
    assert client.get('/api/admin/onsite').status_code==401


def test_onsite_geofence_edit_keeps_original_point(configured,migrated_db):
    client,headers,_=configured
    office_action(client,headers)
    csrf=signin(client).json()['csrf_token']
    before=onsite(client)['items'][0]
    from tests.integration.test_office import POLYGON
    assert client.put('/api/admin/office',headers={'X-CSRF-Token':csrf},json={'name':'Văn phòng mới','address':'Địa chỉ mới','geom':POLYGON,'expected_revision':1}).status_code==200
    data=onsite(client)
    assert data['items'][0]==before
    assert data['office']['revision']==2 and data['office']['name']=='Văn phòng mới'
