import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from app.accounts.service import create_user
from app.config import Settings
from app.db.migrations import apply_migrations,grant_runtime
from app.db.pool import make_pool
from app.main import create_app
from scripts.maintenance import run_once
from scripts.phase6_restore_drill import run_pg
from tests.integration.test_attendance import employee,action
from tests.integration.test_office_attendance import configured,office_action
from tests.test_auth_api import signin

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('backup_policy',['legacy-with-gps','gps-free'])
def test_dump_restore_purge_and_tombstone_before_reopening(configured,migrated_db,test_dsn,tmp_path,backup_policy):
    client,headers,user_id=configured
    now=datetime(2026,10,14,2,tzinfo=timezone.utc)
    # Commit and delete one day through the real Admin API: backup must keep
    # the tombstone, while its reason/session/event/GPS remain absent.
    request_id=str(uuid4())
    body=dict(request_id=request_id,expected_revision=0,expected_work_date='2026-10-14',action='START_REMOTE',reason='Synthetic deleted reason')
    assert client.post('/api/attendance/actions',headers=headers,json=body).status_code==200
    assert action(client,headers,1,'CHECK_OUT','Synthetic close').status_code==200
    day=migrated_db.execute('SELECT id,revision FROM geoattend.attendance_days').fetchone()
    csrf=signin(client).json()['csrf_token']
    assert client.request('DELETE',f'/api/admin/users/{user_id}/history/{day["id"]}',headers={'X-CSRF-Token':csrf},json={'expected_revision':day['revision'],'confirm_username':'worker'}).status_code==200
    csrf=signin(client,'worker','Worker1234').json()['csrf_token'];headers={'X-CSRF-Token':csrf}
    assert office_action(client,headers,revision=3).status_code==200
    # Expired GPS exists physically in backup. Fresh GPS must survive cleanup.
    migrated_db.execute('UPDATE geoattend.office_locations SET recorded_at=%s,expires_at=%s',(now-timedelta(days=30),now))
    other=create_user(migrated_db,'fresh','Synthetic fresh','Fresh1234')
    other_day=migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,'2026-10-14','WORKING_OFFICE') RETURNING id",(other.id,)).fetchone()['id']
    session=migrated_db.execute("INSERT INTO geoattend.work_sessions(day_id,work_mode,start_time) VALUES(%s,'OFFICE',%s) RETURNING id",(other_day,now)).fetchone()['id']
    event=migrated_db.execute("INSERT INTO geoattend.attendance_events(day_id,session_id,event_type,event_time,recorded_at,source,location_verified) VALUES(%s,%s,'WORK_START',%s,%s,'USER',true) RETURNING id",(other_day,session,now,now)).fetchone()['id']
    migrated_db.execute('INSERT INTO geoattend.office_locations(session_id,start_event_id,point,accuracy_m,recorded_at,expires_at) VALUES(%s,%s,ST_SetSRID(ST_MakePoint(106.5,10.5),4326),42,%s,%s)',(session,event,now,now+timedelta(days=30)))
    migrated_db.commit()
    # Weekly PDF is ordinary application data, including in GPS-free backups.
    from tests.integration.test_weekly_reports import upload, PDF
    report=upload(client,headers,week='2026-10-12',filename='Synthetic weekly.pdf')
    assert report.status_code==200,report.text
    report_id=report.json()['id']
    enabled_at=migrated_db.execute("SELECT applied_at FROM geoattend.schema_migrations WHERE name='005_weekly_reports.sql'").fetchone()['applied_at']
    migrated_db.commit()
    backup=tmp_path/'synthetic.dump'
    exclude=('--exclude-table-data=geoattend.office_locations',) if backup_policy=='gps-free' else ()
    run_pg('pg_dump',test_dsn,'--format=custom','--no-owner','--no-privileges',*exclude,'--file',backup)
    target_name='geoattend_test_restore_'+uuid4().hex
    role='restore_runtime_'+uuid4().hex
    with psycopg.connect(test_dsn,autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(target_name)))
        admin.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    target=make_conninfo(test_dsn,dbname=target_name)
    started=__import__('time').perf_counter()
    try:
        run_pg('pg_restore',target,'--no-owner','--no-privileges','--exit-on-error','--dbname',target_name,backup)
        with psycopg.connect(target,row_factory=dict_row) as restored:
            assert apply_migrations(restored,Path('migrations'))==[]
            assert restored.execute("SELECT applied_at FROM geoattend.schema_migrations WHERE name='005_weekly_reports.sql'").fetchone()['applied_at']==enabled_at
            grant_runtime(restored,role);restored.commit()
            assert restored.execute('SELECT count(*) AS n FROM geoattend.office_locations WHERE point IS NOT NULL').fetchone()['n']==(0 if backup_policy=='gps-free' else 2)
            assert restored.execute("SELECT count(*) AS n FROM geoattend.attendance_events WHERE reason='Synthetic deleted reason'").fetchone()['n']==0
        runtime=make_conninfo(target,user=role)
        pool=make_pool(runtime);pool.open()
        try:
            with TestClient(create_app(Settings(),pool)) as restored_client:
                csrf=signin(restored_client,'worker','Worker1234').json()['csrf_token']
                assert restored_client.get('/api/weekly-reports/'+report_id+'/file').content==PDF
                history=restored_client.get('/api/attendance/history?from=2026-10-14&to=2026-10-14')
                assert history.status_code==200
                location=history.json()['items'][0]['sessions'][0]['location']
                if backup_policy=='gps-free':assert location is None
                else:assert location['status']=='expired' and 'longitude' not in location and 'accuracy_m' not in location
                replay=restored_client.post('/api/attendance/actions',headers={'X-CSRF-Token':csrf},json=body)
                assert replay.status_code==409 and replay.json()['code']=='HISTORY_DELETED'
                # This is still a private rehearsal. Do not open the public
                # reverse proxy until maintenance and SQL gates both succeed.
                closed,attempts,sessions,purged=run_once(runtime)
                assert purged==(0 if backup_policy=='gps-free' else 1)
                assert run_once(runtime)[3]==0
                assert restored_client.get('/api/health').status_code==200
                # Recovery must not resurrect sessions revoked after the dump.
                with psycopg.connect(target) as operator:
                    operator.execute('UPDATE geoattend.auth_sessions SET revoked_at=now() WHERE revoked_at IS NULL')
                assert restored_client.get('/api/auth/me').status_code==401
                assert signin(restored_client,'worker','Worker1234').status_code==200
        finally:pool.close()
        with psycopg.connect(runtime,row_factory=dict_row) as restored:
            counts=restored.execute('SELECT count(*) FILTER(WHERE expires_at<=%s AND (point IS NOT NULL OR accuracy_m IS NOT NULL)) AS expired_remaining,count(*) FILTER(WHERE point IS NOT NULL) AS fresh_remaining FROM geoattend.office_locations',(now,)).fetchone()
            assert counts==dict(expired_remaining=0,fresh_remaining=0 if backup_policy=='gps-free' else 1)
            assert restored.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==2
            assert restored.execute("SELECT count(*) AS n FROM geoattend.attendance_events WHERE location_verified=true").fetchone()['n']==2
            assert not restored.execute("SELECT has_schema_privilege(current_user,'geoattend','CREATE') AS allowed").fetchone()['allowed']
            assert not restored.execute("SELECT has_table_privilege(current_user,'geoattend.profiles','DELETE') AS allowed").fetchone()['allowed']
        result=dict(tool='pg_dump custom / pg_restore',backup_policy=backup_policy,expired_hidden_before_purge=True,expired_remaining=0,fresh_remaining=0 if backup_policy=='gps-free' else 1,
                    tombstone_replay='HISTORY_DELETED',migration_checksums='unchanged',runtime_ddl=False,
                    maintenance_second_purge=0,restored_sessions_revoked=True,restore_and_verify_seconds=round(__import__('time').perf_counter()-started,3),
                    backup_bytes=backup.stat().st_size,scope='synthetic isolated local only')
        output=Path('.local-tests/phase-6');output.mkdir(parents=True,exist_ok=True)
        (output/f'restore-{backup_policy}-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    finally:
        # Drop only the exact UUID target created above; never source/app DB.
        with psycopg.connect(test_dsn,autocommit=True) as admin:
            admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(target_name)))
            admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))


def test_reconcile_history_deleted_after_backup_before_reopening(configured,migrated_db,test_dsn,tmp_path):
    client,headers,user_id=configured
    request_id=str(uuid4())
    assert office_action(client,headers,request_id=request_id).status_code==200
    assert action(client,headers,1,'CHECK_OUT','Synthetic end').status_code==200
    day=migrated_db.execute('SELECT id,work_date,revision FROM geoattend.attendance_days').fetchone()
    # This archive intentionally predates deletion and contains GPS, modeling an
    # old archive rather than the GPS-free production backup policy.
    backup=tmp_path/'before-deletion.dump'
    run_pg('pg_dump',test_dsn,'--format=custom','--no-owner','--no-privileges','--file',backup)
    csrf=signin(client).json()['csrf_token']
    deleted=client.request('DELETE',f'/api/admin/users/{user_id}/history/{day["id"]}',headers={'X-CSRF-Token':csrf},json={'expected_revision':day['revision'],'confirm_username':'worker'})
    assert deleted.status_code==200
    ledger={'account_id':str(user_id),'work_date':str(day['work_date'])}
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==0
    target_name='geoattend_test_postdelete_'+uuid4().hex;role='postdelete_runtime_'+uuid4().hex
    with psycopg.connect(test_dsn,autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(target_name)))
        admin.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    target=make_conninfo(test_dsn,dbname=target_name)
    try:
        run_pg('pg_restore',target,'--no-owner','--no-privileges','--exit-on-error','--dbname',target_name,backup)
        with psycopg.connect(target,row_factory=dict_row) as operator:
            grant_runtime(operator,role)
        runtime=make_conninfo(target,user=role)
        run_once(runtime)  # Private restore gate, still no public listener.
        pool=make_pool(runtime);pool.open()
        try:
            with TestClient(create_app(Settings(),pool)) as restored:
                csrf=signin(restored).json()['csrf_token']
                query=f'/api/admin/users/{ledger["account_id"]}/history?from={ledger["work_date"]}&to={ledger["work_date"]}'
                resurrected=restored.get(query).json()['items']
                assert len(resurrected)==1  # Unsafe snapshot, readiness is false.
                assert len(resurrected[0]['sessions'])==1
                assert resurrected[0]['sessions'][0]['location']['status']=='available'
                # Manual runbook procedure: resolve the exact ledger target,
                # load current revision, confirm its username, use existing API.
                target_user=next(row for row in restored.get('/api/admin/users').json()['items'] if row['id']==ledger['account_id'])
                current=resurrected[0]
                assert current['status']=='CHECKED_OUT'
                response=restored.request('DELETE',f'/api/admin/users/{ledger["account_id"]}/history/{current["id"]}',headers={'X-CSRF-Token':csrf},json={'expected_revision':current['revision'],'confirm_username':target_user['username']})
                assert response.status_code==200
                assert restored.get(query).json()['items']==[]
                csrf=signin(restored,'worker','Worker1234').json()['csrf_token']
                replay=office_action(restored,{'X-CSRF-Token':csrf},request_id=request_id)
                assert replay.status_code==409 and replay.json()['code']=='HISTORY_DELETED'
                assert restored.get('/api/attendance/history').json()['items']==[]
        finally:pool.close()
        with psycopg.connect(runtime,row_factory=dict_row) as restored:
            for table in ('work_sessions','attendance_events','office_locations'):
                assert restored.execute(sql.SQL('SELECT count(*) AS n FROM geoattend.{}').format(sql.Identifier(table))).fetchone()['n']==0
            assert restored.execute('SELECT history_deleted FROM geoattend.attendance_days').fetchone()['history_deleted']
            assert restored.execute('SELECT bool_and(history_deleted) AS deleted FROM geoattend.attendance_requests').fetchone()['deleted']
    finally:
        with psycopg.connect(test_dsn,autocommit=True) as admin:
            admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(target_name)))
            admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
