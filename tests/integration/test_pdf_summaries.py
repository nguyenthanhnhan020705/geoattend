import pytest
from tests.integration.test_weekly_reports import reports, upload, PDF2

pytestmark = pytest.mark.integration


def test_queue_is_durable_and_only_one_worker_can_claim(reports, migrated_db):
    from app.reports import summaries as jobs
    client, headers, _, _ = reports
    upload(client, headers)
    assert jobs.discover(migrated_db) == 1
    assert jobs.discover(migrated_db) == 0
    job = jobs.claim(migrated_db)
    assert job and bytes(job['pdf']).startswith(b'%PDF-')
    assert migrated_db.info.transaction_status == 0
    assert jobs.claim(migrated_db) is None
    assert jobs.finish(migrated_db, job, summary='Kết quả đã lưu.') is True
    assert jobs.claim(migrated_db) is None


def test_changed_pdf_cannot_receive_old_summary(reports, migrated_db):
    from app.reports import summaries as jobs
    client, headers, _, _ = reports
    upload(client, headers)
    jobs.discover(migrated_db)
    job = jobs.claim(migrated_db)
    upload(client, headers, revision=1, pdf=PDF2)
    assert jobs.finish(migrated_db, job, summary='Nội dung cũ') is False
    assert jobs.discover(migrated_db) == 1
    new = jobs.claim(migrated_db)
    assert new['content_sha256'] != job['content_sha256']


def test_same_content_new_revision_reuses_complete_summary(reports, migrated_db):
    from app.reports import summaries as jobs
    client, headers, _, _ = reports
    upload(client, headers)
    jobs.discover(migrated_db)
    job = jobs.claim(migrated_db)
    jobs.finish(migrated_db, job, summary='Nội dung giữ nguyên')
    upload(client, headers, revision=1)
    assert jobs.discover(migrated_db) == 0
    assert jobs.claim(migrated_db) is None
    row = migrated_db.execute('SELECT status,summary FROM geoattend.pdf_summaries').fetchone()
    assert row == {'status':'COMPLETE', 'summary':'Nội dung giữ nguyên'}


def test_expired_worker_requires_manual_retry_and_cannot_finish(reports, migrated_db):
    from app.reports import summaries as jobs
    client, headers, _, _ = reports
    upload(client, headers)
    jobs.discover(migrated_db)
    job = jobs.claim(migrated_db)
    migrated_db.execute("UPDATE geoattend.pdf_summaries SET lease_expires_at=now()-interval '1 second'")
    migrated_db.commit()
    assert jobs.claim(migrated_db) is None
    row = migrated_db.execute('SELECT status,error_code FROM geoattend.pdf_summaries').fetchone()
    migrated_db.commit()
    assert row == {'status':'FAILED','error_code':'UNCERTAIN_RESULT'}
    assert jobs.finish(migrated_db, job, summary='Late result') is False


def test_missing_summary_schema_does_not_break_upload(reports, migrated_db):
    from app.reports import summaries as jobs
    client, headers, _, _ = reports
    migrated_db.execute('DROP TABLE geoattend.pdf_summaries')
    migrated_db.commit()
    assert jobs.ready(migrated_db) is False
    assert upload(client, headers).status_code == 200


def test_parallel_connections_claim_only_once(reports,migrated_db,test_dsn):
    from concurrent.futures import ThreadPoolExecutor
    import psycopg
    from psycopg.rows import dict_row
    from app.reports import summaries as jobs
    client,headers,_,_=reports
    upload(client,headers);jobs.discover(migrated_db)
    def claim_one():
        with psycopg.connect(test_dsn,row_factory=dict_row) as conn:
            return jobs.claim(conn)
    with ThreadPoolExecutor(max_workers=2) as executor:
        claims=list(executor.map(lambda _:claim_one(),range(2)))
    assert len([job for job in claims if job])==1
