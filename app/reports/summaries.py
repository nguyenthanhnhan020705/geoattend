"""Durable, content-addressed summaries. No AI calls or attendance writes here."""
from uuid import uuid4


def ready(conn):
    with conn.transaction():
        oid = conn.execute("SELECT to_regclass('geoattend.pdf_summaries') AS oid").fetchone()['oid']
        return bool(oid and conn.execute(
            "SELECT bool_and(has_table_privilege(current_user,%s,p)) AS ok FROM unnest(ARRAY['SELECT','INSERT','UPDATE']) AS p", (oid,)).fetchone()['ok'])


def discover(conn, limit=20):
    with conn.transaction():
        rows = conn.execute('''INSERT INTO geoattend.pdf_summaries(report_id,content_sha256)
            SELECT r.id,r.content_sha256 FROM geoattend.weekly_reports r
            WHERE NOT EXISTS (SELECT 1 FROM geoattend.pdf_summaries s
                WHERE s.report_id=r.id AND s.content_sha256=r.content_sha256)
            ORDER BY r.submitted_at DESC,r.id LIMIT %s
            ON CONFLICT(report_id,content_sha256) DO NOTHING RETURNING id''', (limit,)).fetchall()
    return len(rows)


def claim(conn):
    with conn.transaction():
        # A previous API call might have succeeded: never automatically bill again.
        conn.execute("""UPDATE geoattend.pdf_summaries SET status='FAILED',
            error_code='UNCERTAIN_RESULT',lease_token=NULL,lease_expires_at=NULL,updated_at=now()
            WHERE status='PROCESSING' AND lease_expires_at<=now()""")
        row = conn.execute('''SELECT s.id,r.pdf,r.revision,r.content_sha256,r.id AS report_id
            FROM geoattend.pdf_summaries s JOIN geoattend.weekly_reports r
              ON r.id=s.report_id AND r.content_sha256=s.content_sha256
            WHERE s.status='PENDING' AND s.attempt_count<3
            ORDER BY r.submitted_at DESC,s.created_at,s.id
            LIMIT 1 FOR UPDATE OF s SKIP LOCKED''').fetchone()
        if row is None:
            return None
        token = uuid4()
        conn.execute("""UPDATE geoattend.pdf_summaries SET status='PROCESSING',
            attempt_count=attempt_count+1,lease_token=%s,lease_expires_at=now()+interval '90 seconds',
            error_code=NULL,updated_at=now() WHERE id=%s""", (token,row['id']))
        return {**row,'lease_token':token}


def finish(conn, job, summary=None, error_code=None, model=None, prompt_version=None):
    with conn.transaction():
        row = conn.execute('''UPDATE geoattend.pdf_summaries s SET status=%s,summary=%s,error_code=%s,
            model=%s,prompt_version=%s,lease_token=NULL,lease_expires_at=NULL,updated_at=now()
            WHERE s.id=%s AND s.lease_token=%s AND s.status='PROCESSING' AND s.lease_expires_at>now()
            AND EXISTS (SELECT 1 FROM geoattend.weekly_reports r
              WHERE r.id=s.report_id AND r.content_sha256=s.content_sha256)
            RETURNING s.id''', ('COMPLETE' if summary is not None else 'FAILED',summary,error_code,
                              model,prompt_version,job['id'],job['lease_token'])).fetchone()
    return row is not None
