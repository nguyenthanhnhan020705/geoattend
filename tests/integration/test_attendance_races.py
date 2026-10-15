from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event, Barrier
from uuid import uuid4
import psycopg
from psycopg.rows import dict_row
import pytest
from tests.integration.test_attendance import employee, action

pytestmark=pytest.mark.integration


def test_waiting_lock_past_cutoff_rejected(employee,test_dsn,monkeypatch):
    from app.attendance import service
    from app.attendance.schemas import ActionInput
    from app.errors import ApiError
    _,_,uid=employee
    reached=Event(); original=service.lock_user
    def marked(conn,user_id):
        reached.set()
        return original(conn,user_id)
    monkeypatch.setattr(service,'lock_user',marked)
    def attempt():
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            try: service.act(conn,uid,ActionInput(expected_work_date='2026-10-14',request_id=uuid4(),expected_revision=0,action='START_REMOTE',reason='Home'))
            except ApiError as error: return error.code
    with psycopg.connect(test_dsn) as blocker:
        blocker.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE',(uid,))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(attempt)
            assert reached.wait(10)
            monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13,tzinfo=timezone.utc))
            blocker.commit()
            assert future.result(10)=='DAY_CLOSED'


@pytest.mark.parametrize('same_key',[True,False])
def test_concurrent_remote_starts(employee,test_dsn,migrated_db,same_key):
    from app.attendance import service
    from app.attendance.schemas import ActionInput
    from app.errors import ApiError
    _,_,uid=employee
    keys=[uuid4(),uuid4()]
    if same_key: keys[1]=keys[0]
    gate=Barrier(2)
    def attempt(key):
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            gate.wait(10)
            try: return service.act(conn,uid,ActionInput(expected_work_date='2026-10-14',request_id=key,expected_revision=0,action='START_REMOTE',reason='Home'))
            except ApiError as error: return error.code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(attempt,key) for key in keys]
        responses=[f.result(15) for f in futures]
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n']==1
    if same_key: assert responses[0]==responses[1]
    else: assert sum(r=='STALE_REVISION' for r in responses)==1


def test_checkout_vs_maintenance_one_end(employee,test_dsn,migrated_db,monkeypatch):
    from app.attendance import service
    from app.attendance.schemas import ActionInput
    from app.errors import ApiError
    client,headers,uid=employee
    assert action(client,headers).status_code==200
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13,tzinfo=timezone.utc))
    gate=Barrier(2)
    def work(task):
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            gate.wait(10)
            if task=='worker': return service.maintain(conn)
            try: return service.act(conn,uid,ActionInput(expected_work_date='2026-10-14',request_id=uuid4(),expected_revision=1,action='CHECK_OUT'))
            except ApiError as error: return error.code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(work,t) for t in ('worker','checkout')]
        [f.result(15) for f in futures]
    assert migrated_db.execute("SELECT count(*) AS n FROM geoattend.attendance_events WHERE event_type='WORK_END'").fetchone()['n']==1


def test_inactive_while_waiting_cannot_start(employee,test_dsn,monkeypatch):
    from app.attendance import service
    from app.attendance.schemas import ActionInput
    from app.errors import ApiError
    _,_,uid=employee
    reached=Event(); original=service.lock_user
    def marked(conn,user_id): reached.set(); return original(conn,user_id)
    monkeypatch.setattr(service,'lock_user',marked)
    def attempt():
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            try: service.act(conn,uid,ActionInput(expected_work_date='2026-10-14',request_id=uuid4(),expected_revision=0,action='START_REMOTE',reason='Home'))
            except ApiError as error: return error.status_code
    with psycopg.connect(test_dsn) as blocker:
        blocker.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE',(uid,))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(attempt)
            assert reached.wait(10)
            blocker.execute('UPDATE geoattend.profiles SET is_active=false WHERE id=%s',(uid,)); blocker.commit()
            assert future.result(10)==401


def test_password_reset_while_action_waits_revokes_request(employee,test_dsn,monkeypatch):
    from app.attendance import service
    client,headers,uid=employee
    reached=Event(); original=service.lock_user
    def marked(conn,user_id): reached.set(); return original(conn,user_id)
    monkeypatch.setattr(service,'lock_user',marked)
    with psycopg.connect(test_dsn) as blocker:
        blocker.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE',(uid,))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(action,client,headers)
            assert reached.wait(10)
            blocker.execute('UPDATE geoattend.auth_sessions SET revoked_at=now() WHERE user_id=%s',(uid,))
            blocker.commit()
            assert future.result(10).status_code==401


def test_maintenance_waiting_profile_does_not_block_password_reset(employee,test_dsn,monkeypatch):
    from app.accounts.service import reset_user_password
    from scripts.maintenance import run_once
    client,headers,uid=employee
    assert action(client,headers).status_code==200
    monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13,tzinfo=timezone.utc))
    with psycopg.connect(test_dsn,row_factory=dict_row) as blocker:
        blocker.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE',(uid,))
        with ThreadPoolExecutor(max_workers=1) as executor:
            worker=executor.submit(run_once,test_dsn)
            # Observe the real DB lock wait instead of sleeping or guessing.
            with psycopg.connect(test_dsn,autocommit=True) as observer:
                from time import monotonic
                limit=monotonic()+10
                waiting=False
                while monotonic()<limit:
                    waiting=observer.execute("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE 'SELECT id FROM geoattend.profiles%')").fetchone()[0]
                    if waiting: break
                assert waiting
            reset_user_password(blocker,uid,'Reset12345',datetime(2026,10,14,13,tzinfo=timezone.utc))
            blocker.commit()
            assert worker.result(15)[0]==1


def test_runtime_role_can_start_checkout_and_maintain(employee,migrated_db,test_dsn,monkeypatch):
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from app.db.migrations import grant_runtime
    from app.attendance import service
    from app.attendance.schemas import ActionInput
    _,_,uid=employee
    role='attendance_runtime_'+uuid4().hex
    migrated_db.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    grant_runtime(migrated_db,role); migrated_db.commit()
    try:
        with psycopg.connect(make_conninfo(test_dsn,user=role),row_factory=dict_row) as conn:
            result=service.act(conn,uid,ActionInput(expected_work_date='2026-10-14',request_id=uuid4(),expected_revision=0,action='START_REMOTE',reason='Home'))
            assert result['status']=='WORKING_REMOTE'
            assert service.history(conn,uid,None,None,1,20)['total']==1
            end=service.act(conn,uid,ActionInput(expected_work_date='2026-10-14',request_id=uuid4(),expected_revision=1,action='CHECK_OUT'))
            assert end['status']=='CHECKED_OUT'
            service.act(conn,uid,ActionInput(expected_work_date='2026-10-14',request_id=uuid4(),expected_revision=2,action='START_REMOTE',reason='Again'))
            monkeypatch.setattr('app.clock.utc_now',lambda:datetime(2026,10,14,13,tzinfo=timezone.utc))
            assert service.maintain(conn)==1
    finally:
        migrated_db.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
        migrated_db.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
        migrated_db.commit()


@pytest.mark.parametrize('kind,revision', [('START_LUNCH',1),('START_REMOTE',2)])
@pytest.mark.parametrize('next_time,code', [(datetime(2026,10,14,13,tzinfo=timezone.utc),'DAY_CLOSED'),(datetime(2026,10,14,17,tzinfo=timezone.utc),'STALE_DATE')])
def test_lunch_action_waiting_profile_rechecks_day(employee, test_dsn, migrated_db, monkeypatch, kind, revision, next_time, code):
    from app.attendance import service
    client, headers, uid = employee
    assert action(client,headers).status_code == 200
    if revision == 2:
        assert action(client,headers,1,'START_LUNCH',None).status_code == 200
    reached = Event()
    original = service.lock_user
    def marked(conn,user_id):
        reached.set()
        return original(conn,user_id)
    monkeypatch.setattr(service,'lock_user',marked)
    with psycopg.connect(test_dsn) as blocker:
        blocker.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE',(uid,))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(action,client,headers,revision,kind,'Home' if kind=='START_REMOTE' else None)
            assert reached.wait(10)
            monkeypatch.setattr('app.clock.utc_now',lambda:next_time)
            blocker.commit()
            response = future.result(15)
    assert response.status_code == 409 and response.json()['code'] == code
    assert migrated_db.execute('SELECT status FROM geoattend.attendance_days').fetchone()['status'] == 'CHECKED_OUT'
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.work_sessions').fetchone()['n'] == 1
