import pytest
from app.admin.service import build_snapshot
from app.auth.service import resolve_session
from app.clock import utc_now
from tests.test_auth_api import signin

pytestmark=pytest.mark.integration


def test_dashboard_nonoffice_query_count_does_not_grow_per_employee(api_client,migrated_db):
    """Round trips under the global writer locks must stay bounded for readers."""
    assert signin(api_client).status_code==200
    context=resolve_session(migrated_db,api_client.cookies.get('geoattend_session'),utc_now())
    migrated_db.commit()
    class Counted:
        def __init__(self,conn):self.conn,self.queries=conn,0
        def __getattr__(self,name):return getattr(self.conn,name)
        def execute(self,*args,**kwargs):
            self.queries+=1
            return self.conn.execute(*args,**kwargs)
    def measure():
        counted=Counted(migrated_db)
        data=build_snapshot(counted,context)
        return counted.queries,data
    migrated_db.execute("INSERT INTO geoattend.profiles(username,full_name,password_hash,role) VALUES('query0','Synthetic','unused','USER')")
    migrated_db.commit()
    first,_=measure()
    for index in range(1,10):
        migrated_db.execute("INSERT INTO geoattend.profiles(username,full_name,password_hash,role) VALUES(%s,'Synthetic','unused','USER')",(f'query{index}',))
    migrated_db.commit()
    last,data=measure()
    assert data['total_users']==10 and data['counts']['NOT_STARTED']==10
    assert last<=first+2,(first,last)
