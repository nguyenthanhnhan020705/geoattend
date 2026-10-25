-- Independent derived data. Never alter the existing PDF upload transaction.
-- 007 is reserved for a historical experiment; its checksum stays untouched.
CREATE TABLE geoattend.pdf_summaries (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 report_id uuid NOT NULL REFERENCES geoattend.weekly_reports(id),
 content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
 status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','PROCESSING','COMPLETE','FAILED')),
 summary text,
 error_code text,
 attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count BETWEEN 0 AND 3),
 lease_token uuid,
 lease_expires_at timestamptz,
 model text,
 prompt_version text,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE (report_id, content_sha256),
 CHECK ((status = 'COMPLETE') = (summary IS NOT NULL)),
 CHECK (status <> 'PROCESSING' OR (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL))
);
CREATE INDEX pdf_summaries_pending ON geoattend.pdf_summaries(created_at) WHERE status='PENDING';
