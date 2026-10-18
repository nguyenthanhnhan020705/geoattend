CREATE TABLE geoattend.weekly_reports (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES geoattend.profiles(id),
 week_start date NOT NULL CHECK (extract(isodow FROM week_start)=1),
 filename text NOT NULL CHECK (length(filename) BETWEEN 5 AND 180),
 pdf bytea NOT NULL,
 size_bytes integer NOT NULL CHECK (size_bytes BETWEEN 1 AND 10000000),
 content_sha256 text NOT NULL,
 first_submitted_at timestamptz NOT NULL,
 submitted_at timestamptz NOT NULL,
 revision integer NOT NULL CHECK (revision>0),
 request_id uuid NOT NULL,
 request_hash text NOT NULL,
 CHECK (octet_length(pdf)=size_bytes),
 UNIQUE(user_id,week_start)
);
CREATE INDEX weekly_reports_week ON geoattend.weekly_reports(week_start,user_id);
