from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Event
import time
from uuid import uuid4
import psycopg
from psycopg.rows import dict_row
import pytest
from app.auth.service import resolve_session
from app.errors import ApiError
from tests.integration.test_weekly_reports import reports, PDF, PDF2, upload

pytestmark=pytest.mark.integration


def context_for(client,db,now):
    context=resolve_session(db,client.cookies.get('geoattend_session'),now)
    db.commit()
    return context


@pytest.mark.parametrize('case',['deadline','revoked'])
def test_upload_rechecks_after_waiting_profile_lock(reports,migrated_db,test_dsn,case):
    from app.reports.service import submit
    client,headers,clock,ids=reports
    context=context_for(client,migrated_db,clock['now'])
    entered=Event()
    backend=[]
    def contender():
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            backend.append(conn.info.backend_pid)
            entered.set()
            try:
                submit(conn,context,date(2026,10,19),uuid4(),0,'race.pdf',PDF)
            except ApiError as error:
                return error.code
    with ThreadPoolExecutor(max_workers=1) as executor:
        with migrated_db.transaction():
            migrated_db.execute('SELECT id FROM geoattend.profiles WHERE id=%s FOR UPDATE',(ids[0],))
            future=executor.submit(contender)
            assert entered.wait(5)
            # Observe the real database lock wait before moving clock/session.
            for _ in range(200):
                blocked=migrated_db.execute('SELECT cardinality(pg_blocking_pids(%s)) AS n',(backend[0],)).fetchone()['n']
                if blocked:break
                time.sleep(.01)
            assert blocked
            if case=='deadline':
                clock['now']=datetime(2026,10,25,17,tzinfo=timezone.utc)
                # Keep the session valid across our controlled multi-day jump.
                migrated_db.execute("UPDATE geoattend.auth_sessions SET expires_at='2026-10-27 00:00+00' WHERE id=%s",(context.session_id,))
            else:
                migrated_db.execute('UPDATE geoattend.auth_sessions SET revoked_at=%s WHERE id=%s',(clock['now'],context.session_id))
        assert future.result(timeout=10)==('REPORT_WEEK_CLOSED' if case=='deadline' else 'AUTH_REQUIRED')
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.weekly_reports').fetchone()['n']==0


def test_concurrent_replacement_rejects_stale_writer(reports,migrated_db,test_dsn):
    from app.reports.service import submit
    client,headers,clock,ids=reports
    assert upload(client,headers).status_code==200
    context=context_for(client,migrated_db,clock['now'])
    def contender(pdf):
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            try:
                return submit(conn,context,date(2026,10,19),uuid4(),1,'race.pdf',pdf)['revision']
            except ApiError as error:
                return error.code
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=list(executor.map(contender,[PDF,PDF2]))
    assert set(results)=={2,'STALE_REVISION'}
    assert migrated_db.execute('SELECT revision FROM geoattend.weekly_reports').fetchone()['revision']==2
