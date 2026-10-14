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
            try: service.act(conn,uid,ActionInput(request_id=uuid4(),expected_revision=0,action='START_REMOTE',reason='Home'))
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
            try: return service.act(conn,uid,ActionInput(request_id=key,expected_revision=0,action='START_REMOTE',reason='Home'))
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
            try: return service.act(conn,uid,ActionInput(request_id=uuid4(),expected_revision=1,action='CHECK_OUT'))
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
            try: service.act(conn,uid,ActionInput(request_id=uuid4(),expected_revision=0,action='START_REMOTE',reason='Home'))
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
