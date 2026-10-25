import pytest
from tests.integration.test_weekly_reports import reports, upload, PDF2
from tests.test_auth_api import signin

pytestmark=pytest.mark.integration


def test_only_admin_can_read_or_retry_summary(reports,migrated_db):
    client,headers,_,_=reports
    report=upload(client,headers).json()
    path=f"/api/weekly-reports/{report['id']}/summary?expected_revision=1"
    for route in (path,path.replace('/api/','/api/admin/')):
        assert client.get(route).status_code==403
        assert client.post(route,headers=headers).status_code==403
    from app.reports import summaries
    summaries.discover(migrated_db)
    job=summaries.claim(migrated_db)
    summaries.finish(migrated_db,job,error_code='AI_TIMEOUT')
    assert client.post(path,headers=headers).status_code==403
    assert migrated_db.execute('SELECT status FROM geoattend.pdf_summaries').fetchone()['status']=='FAILED'
    migrated_db.commit()
    signin(client,'other','Worker1234')
    assert client.get(path).status_code==403
    assert client.get(path.replace('/api/','/api/admin/')).status_code==403
    headers={'X-CSRF-Token':signin(client).json()['csrf_token']}
    assert client.get(path.replace('/api/','/api/admin/')).json()['status']=='FAILED'
    assert client.post(path).status_code==403
    response=client.post(path,headers=headers)
    assert response.status_code==200 and response.json()['status']=='PENDING'
    assert client.post(path,headers=headers).status_code==409
    result=client.get(path.replace('/api/','/api/admin/'))
    assert result.status_code==200 and result.json()['status']=='PENDING'
    assert 'pdf' not in result.text and 'lease_token' not in result.text


def test_stale_summary_and_pdf_are_rejected(reports):
    client,headers,_,_=reports
    report=upload(client,headers).json()
    upload(client,headers,revision=1,pdf=PDF2)
    result=client.get(f"/api/weekly-reports/{report['id']}/file?expected_revision=1")
    assert result.status_code==409 and result.json()['code']=='STALE_REVISION'
    signin(client)
    result=client.get(f"/api/admin/weekly-reports/{report['id']}/summary?expected_revision=1")
    assert result.status_code==409 and result.json()['code']=='STALE_REVISION'


def test_cached_summary_and_retry_cap(reports,migrated_db):
    from app.reports import summaries
    client,headers,_,_=reports
    report=upload(client,headers).json()
    headers={'X-CSRF-Token':signin(client).json()['csrf_token']}
    path=f"/api/weekly-reports/{report['id']}/summary?expected_revision=1"
    summaries.discover(migrated_db)
    for _ in range(3):
        job=summaries.claim(migrated_db)
        summaries.finish(migrated_db,job,error_code='RATE_LIMIT')
        result=client.get(path).json()
        if result['can_retry']:
            assert client.post(path,headers=headers).status_code==200
    assert result['can_retry'] is False
    assert client.post(path,headers=headers).status_code==409


def test_missing_summary_schema_is_separate_from_reports(reports,migrated_db):
    client,headers,_,_=reports
    report=upload(client,headers).json()
    migrated_db.execute('DROP TABLE geoattend.pdf_summaries');migrated_db.commit()
    assert client.get(f"/api/weekly-reports/{report['id']}/file").status_code==200
    assert upload(client,headers,revision=1,pdf=PDF2).status_code==200
    signin(client)
    assert client.get(f"/api/admin/weekly-reports/{report['id']}/summary?expected_revision=2").status_code==503


def test_worker_releases_connection_before_ai_and_handles_errors(reports,migrated_db,test_dsn,monkeypatch):
    import psycopg
    from scripts.pdf_summary_worker import process_one
    from app.reports.summary_provider import SummaryError
    client,headers,_,_=reports
    upload(client,headers)
    opened=[]
    connect=psycopg.connect
    def track(*args,**kwargs):
        conn=connect(*args,**kwargs);opened.append(conn);return conn
    monkeypatch.setattr(psycopg,'connect',track)
    class Provider:
        model='test'
        def summarize(self,pdf):
            assert opened and all(conn.closed for conn in opened)
            raise SummaryError('UNREADABLE')
    assert process_one(test_dsn,Provider()) is True
    row=migrated_db.execute('SELECT status,error_code FROM geoattend.pdf_summaries').fetchone()
    assert row=={'status':'FAILED','error_code':'UNREADABLE'}


def test_worker_success_is_cached_and_existing_files_are_discovered(reports,migrated_db,test_dsn):
    from scripts.pdf_summary_worker import process_one
    from tests.pdf_fixtures import text_pdf
    from tests.test_pdf_summary_provider import TEXT
    client,headers,_,_=reports
    report=upload(client,headers,pdf=text_pdf()).json()
    class Provider:
        model='test'
        def summarize(self,pdf): return TEXT.strip()
    assert process_one(test_dsn,Provider()) is True
    class MustNotRun:
        model='test'
        def summarize(self,pdf): raise AssertionError('Cached PDF called AI again')
    assert process_one(test_dsn,MustNotRun()) is False
    signin(client)
    for _ in range(3):
        result=client.get(f"/api/admin/weekly-reports/{report['id']}/summary?expected_revision=1")
        assert result.json()['summary']==TEXT.strip()
    assert migrated_db.execute('SELECT attempt_count FROM geoattend.pdf_summaries').fetchone()['attempt_count']==1


def test_revoked_session_cannot_read_or_retry_summary(reports,migrated_db):
    client,headers,_,_=reports
    report=upload(client,headers).json()
    headers={'X-CSRF-Token':signin(client).json()['csrf_token']}
    migrated_db.execute('UPDATE geoattend.auth_sessions SET revoked_at=now()');migrated_db.commit()
    path=f"/api/weekly-reports/{report['id']}/summary?expected_revision=1"
    assert client.get(path).status_code==401
    assert client.post(path,headers=headers).status_code==401


def test_dry_run_leaves_existing_pdf_and_queue_unchanged(reports,migrated_db,test_dsn):
    import os,subprocess,sys
    client,headers,_,_=reports
    upload(client,headers)
    env=os.environ.copy();env['GEOATTEND_DATABASE_URL']=test_dsn
    env.pop('GEOATTEND_GEMINI_API_KEY',None)
    run=subprocess.run([sys.executable,'-m','scripts.pdf_summary_worker','--dry-run'],env=env,capture_output=True)
    assert run.returncode==0
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.pdf_summaries').fetchone()['n']==0
    assert migrated_db.execute('SELECT revision FROM geoattend.weekly_reports').fetchone()['revision']==1


def test_summary_uses_same_owner_role_policy_as_pdf(reports,migrated_db):
    from app.reports import summaries
    client,headers,_,ids=reports
    report=upload(client,headers).json()
    summaries.discover(migrated_db);job=summaries.claim(migrated_db)
    summaries.finish(migrated_db,job,summary='Private derived content')
    migrated_db.execute("UPDATE geoattend.profiles SET role='USER' WHERE role='ADMIN'")
    migrated_db.execute("UPDATE geoattend.profiles SET role='ADMIN' WHERE id=%s",(ids[0],))
    migrated_db.commit()
    admin_headers={'X-CSRF-Token':signin(client,'worker','Worker1234').json()['csrf_token']}
    path=f"/api/admin/weekly-reports/{report['id']}"
    assert client.get(path+'/file').status_code==404
    assert client.get(path+'/summary?expected_revision=1').status_code==404
    assert client.post(path+'/summary?expected_revision=1',headers=admin_headers).status_code==404
