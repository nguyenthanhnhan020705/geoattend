from datetime import datetime, timezone
from uuid import uuid4
from urllib.parse import quote
import pytest
from tests.test_auth_api import signin

pytestmark = pytest.mark.integration
PDF = b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n'
PDF2 = b'%PDF-1.7\n2 0 obj<</Type/Catalog>>endobj\n%%EOF\n'


@pytest.fixture
def reports(api_client, migrated_db, monkeypatch):
    clock = {'now': datetime(2026,10,21,2,tzinfo=timezone.utc)}
    monkeypatch.setattr('app.clock.utc_now', lambda: clock['now'])
    monkeypatch.setattr('app.auth.dependencies.utc_now', lambda: clock['now'])
    monkeypatch.setattr('app.auth.routes.utc_now', lambda: clock['now'])
    # Enable before our controlled reporting week, independently of wall clock.
    migrated_db.execute("UPDATE geoattend.schema_migrations SET applied_at='2026-10-12 00:00+00' WHERE name='005_weekly_reports.sql'")
    migrated_db.commit()
    admin_csrf = signin(api_client).json()['csrf_token']
    ids = []
    for name in ('worker','other'):
        response = api_client.post('/api/admin/users', headers={'X-CSRF-Token':admin_csrf},
            json={'username':name,'full_name':'Nhân viên '+name,'password':'Worker1234'})
        assert response.status_code == 201
        ids.append(response.json()['id'])
    migrated_db.execute("UPDATE geoattend.profiles SET created_at='2026-10-12 00:00+00' WHERE role='USER'")
    migrated_db.commit()
    csrf = signin(api_client,'worker','Worker1234').json()['csrf_token']
    return api_client, {'X-CSRF-Token':csrf}, clock, ids


def upload(client, headers, *, week='2026-10-19', revision=0, key=None, pdf=PDF, filename='Báo cáo.pdf'):
    return client.put('/api/weekly-reports/'+week,
        params={'request_id':str(key or uuid4()),'expected_revision':revision},
        headers={**headers,'Content-Type':'application/pdf','X-Report-Filename':quote(filename,safe='')},content=pdf)


def test_submit_replace_download_and_retry(reports, migrated_db):
    client, headers, _, _ = reports
    key = uuid4()
    first = upload(client,headers,key=key)
    assert first.status_code == 200, first.text
    data = first.json()
    assert data['revision'] == 1 and data['filename'] == 'Báo cáo.pdf'
    assert upload(client,headers,key=key).json() == data
    assert upload(client,headers,key=key,pdf=PDF2).json()['code'] == 'REQUEST_CONFLICT'
    replacement = upload(client,headers,revision=1,pdf=PDF2)
    assert replacement.status_code == 200
    assert replacement.json()['id'] == data['id'] and replacement.json()['revision'] == 2
    assert upload(client,headers,key=key).json()['code'] == 'STALE_REVISION'
    response = client.get('/api/weekly-reports/'+data['id']+'/file')
    assert response.content == PDF2 and response.headers['content-type'] == 'application/pdf'
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert 'inline;' in response.headers['content-disposition']
    assert 'attachment;' in client.get('/api/weekly-reports/'+data['id']+'/file?download=true').headers['content-disposition']
    history = client.get('/api/weekly-reports').json()
    assert history['total'] == 1 and history['items'][0]['revision'] == 2
    assert not {'pdf','content_sha256','request_id','request_hash'} & set(history['items'][0])
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.weekly_reports').fetchone()['n'] == 1


def test_deadline_future_week_and_replay_after_deadline(reports,migrated_db):
    client,headers,clock,_ = reports
    clock['now'] = datetime(2026,10,25,16,59,59,tzinfo=timezone.utc)
    signin(client,'worker','Worker1234')  # renew under the controlled clock
    headers={'X-CSRF-Token':client.get('/api/auth/me').json()['csrf_token']}
    key=uuid4()
    first=upload(client,headers,key=key)
    assert first.status_code == 200
    assert upload(client,headers,week='2026-10-26').json()['code'] == 'FUTURE_WEEK'
    assert upload(client,headers,week='2026-10-20').status_code == 422
    clock['now'] = datetime(2026,10,25,17,tzinfo=timezone.utc)
    assert upload(client,headers,revision=1,pdf=PDF2).json()['code'] == 'REPORT_WEEK_CLOSED'
    assert upload(client,headers,key=key).json() == first.json()
    assert client.get('/api/weekly-reports/status').json()['week_start'] == '2026-10-26'
    assert upload(client,headers,week='2026-10-26').status_code == 200


def test_reminders_and_activation_without_retroactive_missing(reports,migrated_db):
    client,headers,clock,ids=reports
    clock['now']=datetime(2026,10,25,2,tzinfo=timezone.utc)
    signin(client,'worker','Worker1234')
    headers={'X-CSRF-Token':client.get('/api/auth/me').json()['csrf_token']}
    notices=client.get('/api/weekly-reports/status').json()['notices']
    assert {n['message'] for n in notices} == {
        'BẠN CÒN 1 NGÀY ĐỂ NỘP BÁO CÁO NHÉ!!',
        'TUẦN VỪA RỒI BẠN CHƯA NỘP BÁO CÁO. HÃY TRÌNH BÀY NỘI DUNG ĐÓ GỘP VỚI TUẦN NÀY NHÉ!'}
    assert upload(client,headers).status_code == 200
    assert [n['code'] for n in client.get('/api/weekly-reports/status').json()['notices']] == ['PREVIOUS_WEEK_MISSING']
    migrated_db.execute("UPDATE geoattend.schema_migrations SET applied_at='2026-10-20 00:00+00' WHERE name='005_weekly_reports.sql'")
    migrated_db.commit()
    assert client.get('/api/weekly-reports/status').json()['notices'] == []


def test_pdf_rejection_keeps_current_and_checks_auth(reports,migrated_db):
    client,headers,_,ids=reports
    first=upload(client,headers).json()
    assert upload(client,headers,revision=1,pdf=b'<html>not pdf').status_code == 422
    assert upload(client,headers,revision=1,pdf=b'%PDF-1.4\n'+b'x'*10_000_000).status_code == 413
    assert upload(client,{},revision=1).status_code == 403
    assert upload(client,{**headers,'Origin':'https://evil.example'},revision=1).status_code == 403
    assert client.get('/api/weekly-reports/'+first['id']+'/file').content == PDF
    signin(client,'other','Worker1234')
    assert client.get('/api/weekly-reports/'+first['id']+'/file').status_code == 404
    assert client.get('/api/admin/weekly-reports').status_code == 403
    admin=signin(client).json()
    assert upload(client,{'X-CSRF-Token':admin['csrf_token']}).status_code == 403
    assert client.get('/api/admin/weekly-reports/'+first['id']+'/file').content == PDF
    migrated_db.execute('UPDATE geoattend.profiles SET is_active=false WHERE id=%s',(ids[0],));migrated_db.commit()
    items=client.get('/api/admin/weekly-reports').json()['items']
    worker=next(x for x in items if x['id']==ids[0])
    assert worker['status']=='SUBMITTED' and worker['is_active'] is False
    filtered=client.get('/api/admin/weekly-reports',params={'user_id':ids[0],'week_start':'2026-10-19'}).json()
    assert filtered['total']==1
    assert client.get('/api/admin/weekly-reports?week_start=2026-10-05').json()['items'][0]['status']=='NOT_APPLICABLE'


def test_filename_is_safe_and_pending_overdue_status(reports):
    client,headers,clock,_=reports
    first=upload(client,headers,filename='../Báo "cáo\r\nInjected: true.pdf').json()
    response=client.get('/api/weekly-reports/'+first['id']+'/file')
    assert response.status_code==200 and 'Injected' not in response.headers
    assert '\r' not in first['filename'] and '\n' not in first['filename'] and '/' not in first['filename']
    signin(client)
    items=client.get('/api/admin/weekly-reports').json()['items']
    assert {i['status'] for i in items}=={'SUBMITTED','PENDING'}
    previous=client.get('/api/admin/weekly-reports?week_start=2026-10-12').json()['items']
    assert {i['status'] for i in previous}=={'OVERDUE'}


def test_replacement_database_failure_rolls_back(reports,migrated_db):
    from psycopg import Error
    from app.reports import service
    from app.auth.service import resolve_session
    client,headers,clock,ids=reports
    first=upload(client,headers).json()
    context=resolve_session(migrated_db,client.cookies.get('geoattend_session'),clock['now'])
    migrated_db.commit()
    migrated_db.execute("CREATE FUNCTION geoattend.reject_report() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'fixture'; END $$")
    migrated_db.execute('CREATE TRIGGER reject_report BEFORE UPDATE ON geoattend.weekly_reports FOR EACH ROW EXECUTE FUNCTION geoattend.reject_report()')
    migrated_db.commit()
    with pytest.raises(Error):
        service.submit(migrated_db,context,datetime(2026,10,19).date(),uuid4(),1,'new.pdf',PDF2)
    assert client.get('/api/weekly-reports/'+first['id']+'/file').content==PDF


def test_upload_size_stream_and_revoked_session(reports,migrated_db):
    client,headers,clock,ids=reports
    params={'request_id':str(uuid4()),'expected_revision':0}
    response=client.put('/api/weekly-reports/2026-10-19',params=params,
        headers={**headers,'Content-Type':'application/pdf','X-Report-Filename':'report.pdf'},
        content=iter([b'%PDF-1.4\n',b'x'*5_000_000,b'x'*5_000_000,b'%%EOF']))
    assert response.status_code==413
    assert migrated_db.execute('SELECT count(*) AS n FROM geoattend.weekly_reports').fetchone()['n']==0
    migrated_db.execute('UPDATE geoattend.auth_sessions SET revoked_at=%s WHERE user_id=%s',(clock['now'],ids[0]));migrated_db.commit()
    assert upload(client,headers).status_code==401


def test_filename_header_does_not_put_private_filename_in_access_log_url(reports):
    from urllib.parse import quote
    client,headers,_,_=reports
    name='Báo cáo riêng.pdf'
    response=client.put('/api/weekly-reports/2026-10-19',
        params={'request_id':str(uuid4()),'expected_revision':0},
        headers={**headers,'Content-Type':'application/pdf','X-Report-Filename':quote(name,safe='')},content=PDF)
    assert response.status_code==200
    assert response.json()['filename']==name
    assert 'filename' not in response.request.url.params


def test_report_schema_constraints_and_runtime_grants(reports,migrated_db,test_dsn):
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from app.db.migrations import grant_runtime
    client,headers,clock,ids=reports
    first=upload(client,headers)
    assert first.status_code==200
    row=migrated_db.execute('SELECT * FROM geoattend.weekly_reports').fetchone()
    migrated_db.commit()
    for assignment,args in [('week_start=%s',('2026-10-20',)),('size_bytes=%s',(0,)),('pdf=%s',(PDF2+b' ',))]:
        with pytest.raises(psycopg.Error):
            with migrated_db.transaction():
                migrated_db.execute('UPDATE geoattend.weekly_reports SET '+assignment+' WHERE id=%s',(*args,row['id']))
    role='reports_runtime_'+uuid4().hex
    migrated_db.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    grant_runtime(migrated_db,role);migrated_db.commit()
    try:
        from psycopg.rows import dict_row
        from app.auth.service import resolve_session
        from app.reports import service
        with psycopg.connect(make_conninfo(test_dsn,user=role),row_factory=dict_row) as runtime:
            context=resolve_session(runtime,client.cookies.get('geoattend_session'),clock['now'])
            runtime.commit()
            assert service.status(runtime,context)['report']['revision']==1
            assert service.submit(runtime,context,datetime(2026,10,19).date(),uuid4(),1,'runtime.pdf',PDF2)['revision']==2
        with psycopg.connect(make_conninfo(test_dsn,user=role)) as runtime:
            assert runtime.execute('SELECT size_bytes FROM geoattend.weekly_reports').fetchone()[0]==len(PDF)
            runtime.execute('UPDATE geoattend.weekly_reports SET filename=filename')
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with runtime.transaction():runtime.execute('DELETE FROM geoattend.weekly_reports')
    finally:
        migrated_db.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
        migrated_db.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)));migrated_db.commit()
