"""Real HTTP + PostGIS load; fixture refuses application DSNs and owns its DB.

Default is a small reproducible smoke. Set GEOATTEND_LOAD_ROUNDS=10 for a
longer measurement. Reports contain aggregate data only, never response bodies.
"""
import json
import os
import platform
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import uvicorn

from app.accounts.bootstrap import create_initial_admin
from app.accounts.service import create_user
from app.config import Settings
from app.db.pool import make_pool
from app.main import create_app
from app.telemetry import ApiTiming
from scripts.phase6_load import summarize
from tests.integration.test_office import POLYGON

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('concurrency',[1,10,20])
def test_local_backend_load(migrated_db,test_dsn,monkeypatch,concurrency):
    now=datetime(2026,10,16,2,tzinfo=timezone.utc)
    monkeypatch.setattr('app.clock.utc_now',lambda:now)
    monkeypatch.setattr('app.auth.routes.utc_now',lambda:now)
    monkeypatch.setattr('app.auth.dependencies.utc_now',lambda:now)
    rounds=int(os.getenv('GEOATTEND_LOAD_ROUNDS','1'))
    assert 1<=rounds<=100
    create_initial_admin(migrated_db,'admin','Synthetic Admin','Synthetic1234')
    users=[create_user(migrated_db,f'load{i:02}','Synthetic User','Synthetic1234') for i in range(10)]
    migrated_db.execute('INSERT INTO geoattend.office(name,address,geom,revision) VALUES(%s,%s,ST_GeomFromGeoJSON(%s),1)',('Synthetic Office','Synthetic',json.dumps(POLYGON)))
    for user in users:
        for offset in range(1,6):
            day=migrated_db.execute("INSERT INTO geoattend.attendance_days(user_id,work_date,status) VALUES(%s,%s,'CHECKED_OUT') RETURNING id",(user.id,now.date()-timedelta(days=offset))).fetchone()['id']
            session=migrated_db.execute("INSERT INTO geoattend.work_sessions(day_id,work_mode,start_time,end_time,end_source,start_reason) VALUES(%s,'REMOTE',%s,%s,'USER','Synthetic') RETURNING id",(day,now-timedelta(days=offset),now-timedelta(days=offset)+timedelta(hours=8))).fetchone()['id']
            for kind,moment in [('WORK_START',now-timedelta(days=offset)),('WORK_END',now-timedelta(days=offset)+timedelta(hours=8))]:
                migrated_db.execute("INSERT INTO geoattend.attendance_events(day_id,session_id,event_type,event_time,recorded_at,source) VALUES(%s,%s,%s,%s,%s,'USER')",(day,session,kind,moment,moment))
    migrated_db.commit()
    pool=make_pool(test_dsn);pool.open()
    samples=[];guard=threading.Lock()
    def record(sample):
        with guard:samples.append(sample)
    sock=socket.socket();sock.bind(('127.0.0.1',0))
    origin=f'http://127.0.0.1:{sock.getsockname()[1]}'
    app=ApiTiming(create_app(Settings(origin=origin),pool),record)
    server=uvicorn.Server(uvicorn.Config(app,log_level='critical',access_log=False))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    clients=[]
    try:
        for _ in range(200):
            if server.started:break
            time.sleep(.05)
        assert server.started
        # Setup/warmup excluded explicitly; login is measured separately below.
        for name in [f'load{i:02}' for i in range(10)]+['admin']:
            client=httpx.Client(base_url=origin,timeout=30,trust_env=False)
            response=client.post('/api/auth/login',json={'username':name,'password':'Synthetic1234'})
            assert response.status_code==200
            client.headers['X-CSRF-Token']=response.json()['csrf_token']
            clients.append(client)
            assert client.get('/api/auth/me').status_code==200
        with guard:samples.clear()
        start=time.perf_counter()
        response=clients[-1].post('/api/auth/login',json={'username':'admin','password':'Synthetic1234'})
        assert response.status_code==200
        clients[-1].headers['X-CSRF-Token']=response.json()['csrf_token']
        def writer(index):
            client=clients[index];revision=0
            response=client.post('/api/auth/login',json={'username':f'load{index:02}','password':'Synthetic1234'})
            assert response.status_code==200
            client.headers['X-CSRF-Token']=response.json()['csrf_token']
            def perform(kind,reason=None,replay=False):
                nonlocal revision
                body=dict(request_id=str(uuid4()),expected_work_date=str(now.date()),expected_revision=revision,action=kind)
                if kind.endswith('OFFICE'):body.update(latitude=10.5,longitude=106.5,accuracy_m=50000)
                elif reason is not None:body['reason']=reason
                result=client.post('/api/attendance/actions',json=body)
                assert result.status_code==200,(kind,result.status_code)
                revision=result.json()['revision']
                if replay:
                    retry=client.post('/api/attendance/actions',json=body)
                    assert retry.status_code==200 and retry.json()==result.json()
            if index==9:
                perform('FULL_DAY_LEAVE','Synthetic leave',True)
            else:
                if index==8:perform('MORNING_LEAVE','Synthetic morning')
                perform('START_OFFICE' if index%2==0 else 'START_REMOTE','Synthetic remote',True)
                if index!=8:
                    perform('START_LUNCH')
                    perform('START_REMOTE' if index%2==0 else 'START_OFFICE','Synthetic resume')
            for _ in range(rounds):
                assert client.get('/api/attendance/status').status_code==200
                assert client.get('/api/attendance/history').status_code==200
                if index not in (8,9):
                    current=client.get('/api/attendance/status').json()['status']
                    perform('SWITCH_REMOTE' if current=='WORKING_OFFICE' else 'SWITCH_OFFICE','Synthetic switch')
            if index!=9:perform('CHECK_OUT')
        def reader(index):
            # Sharing a read-only cookie jar; these endpoints never set cookies.
            client=clients[-1]
            for _ in range(rounds*2):
                for path in ['/api/admin/dashboard','/api/admin/onsite',f'/api/admin/users/{users[index].id}/history','/api/health']:
                    assert client.get(path).status_code==200
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures=[executor.submit(writer,i) for i in range(10)]+[executor.submit(reader,i) for i in range(10)]
            failures=[]
            for future in futures:
                try:future.result()
                except Exception as error:failures.append(type(error).__name__)
        elapsed=time.perf_counter()-start
        result=summarize(samples)
        result.update(concurrency=concurrency,rounds=rounds,workload_failures=failures,elapsed_seconds=round(elapsed,3),
                      requests_per_second=round(len(samples)/elapsed,2),users=10,history_days=5,
                      python=platform.python_version(),platform=platform.platform(),
                      cpu_count=os.cpu_count(),pool_max_size=5,uvicorn_workers=1,
                      clock='2026-10-16 09:00 Vietnam (controlled business time; monotonic timing real)',
                      postgres=migrated_db.execute('SHOW server_version').fetchone()['server_version'],
                      postgis=migrated_db.execute('SELECT postgis_lib_version() AS version').fetchone()['version'])
        output=Path('.local-tests/phase-6');output.mkdir(parents=True,exist_ok=True)
        (output/f'load-c{concurrency}-r{rounds}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        assert not failures,failures
        assert result['errors']==0
        assert result['successful_within_2s_percent']>=95,result
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions WHERE end_time IS NULL').fetchone()['n']==0
        assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.attendance_days WHERE history_deleted=false').fetchone()['n']==60
    finally:
        for client in clients:client.close()
        server.should_exit=True;thread.join(15);sock.close();pool.close()
