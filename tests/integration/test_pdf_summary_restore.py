"""Verify summary persistence with the application's real backup tools."""
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from app.db.migrations import apply_migrations, grant_runtime
from app.reports import summaries
from scripts.phase6_restore_drill import run_pg
from tests.integration.test_weekly_reports import reports, upload, PDF

pytestmark = pytest.mark.integration


def test_summary_and_pdf_survive_restore_without_another_ai_call(
    reports, migrated_db, test_dsn, tmp_path,
):
    client, headers, _, _ = reports
    response = upload(client, headers)
    assert response.status_code == 200
    report_id = response.json()['id']
    assert summaries.discover(migrated_db) == 1
    job = summaries.claim(migrated_db)
    text = 'Bản tóm tắt tổng hợp dùng để kiểm tra khôi phục dữ liệu.'
    assert summaries.finish(migrated_db, job, summary=text)
    before = migrated_db.execute(
        'SELECT report_id,content_sha256,status,summary,attempt_count,model,prompt_version '
        'FROM geoattend.pdf_summaries'
    ).fetchone()
    activation = migrated_db.execute(
        'SELECT name,checksum,applied_at FROM geoattend.schema_migrations ORDER BY name'
    ).fetchall()
    migrated_db.commit()
    archive = tmp_path / 'summary.dump'
    run_pg('pg_dump', test_dsn, '--format=custom', '--no-owner', '--no-privileges',
           '--exclude-table-data=geoattend.office_locations', '--file', archive)
    name = 'geoattend_test_pdf_restore_' + uuid4().hex
    role = 'pdf_restore_' + uuid4().hex
    with psycopg.connect(test_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        admin.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    target = make_conninfo(test_dsn, dbname=name)
    try:
        run_pg('pg_restore', target, '--no-owner', '--no-privileges',
               '--exit-on-error', '--dbname', name, archive)
        with psycopg.connect(target, row_factory=dict_row) as restored:
            assert apply_migrations(restored, Path('migrations')) == []
            grant_runtime(restored, role)
            restored.commit()
            assert restored.execute(
                'SELECT name,checksum,applied_at FROM geoattend.schema_migrations ORDER BY name'
            ).fetchall() == activation
        with psycopg.connect(make_conninfo(target, user=role), row_factory=dict_row) as runtime:
            row = runtime.execute(
                'SELECT report_id,content_sha256,status,summary,attempt_count,model,prompt_version '
                'FROM geoattend.pdf_summaries'
            ).fetchone()
            assert row == before
            report = runtime.execute(
                'SELECT pdf,content_sha256,revision FROM geoattend.weekly_reports WHERE id=%s',
                (report_id,),
            ).fetchone()
            assert bytes(report['pdf']) == PDF
            assert report['content_sha256'] == row['content_sha256']
            assert report['revision'] == 1
            runtime.commit()
            assert summaries.ready(runtime)
            runtime.commit()
            assert summaries.discover(runtime) == 0
            assert summaries.claim(runtime) is None
            assert not runtime.execute(
                "SELECT has_schema_privilege(current_user,'geoattend','CREATE') AS allowed"
            ).fetchone()['allowed']
            assert not runtime.execute(
                "SELECT has_table_privilege(current_user,'geoattend.pdf_summaries','DELETE') AS allowed"
            ).fetchone()['allowed']
    finally:
        with psycopg.connect(test_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
            admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
