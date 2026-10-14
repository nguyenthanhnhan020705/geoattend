CREATE TABLE geoattend.office (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 name text NOT NULL,
 address text NOT NULL,
 geom geometry(Polygon,4326),
 revision integer NOT NULL DEFAULT 0,
 updated_at timestamptz NOT NULL DEFAULT now(),
 CHECK (geom IS NULL OR (ST_IsValid(geom) AND NOT ST_IsEmpty(geom) AND ST_Area(geom)>0))
);
CREATE UNIQUE INDEX single_office ON geoattend.office((true));
CREATE INDEX office_geom ON geoattend.office USING gist(geom);
CREATE TABLE geoattend.attendance_days (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES geoattend.profiles(id),
 work_date date NOT NULL,
 status text NOT NULL CHECK (status IN ('NOT_STARTED','WORKING_OFFICE','WORKING_REMOTE','LUNCH_BREAK','MORNING_LEAVE','FULL_DAY_LEAVE','CHECKED_OUT')),
 revision integer NOT NULL DEFAULT 0,
 updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(user_id,work_date)
);
CREATE TABLE geoattend.work_sessions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 day_id uuid NOT NULL REFERENCES geoattend.attendance_days(id),
 work_mode text NOT NULL CHECK (work_mode IN ('OFFICE','REMOTE')),
 start_time timestamptz NOT NULL,
 end_time timestamptz,
 start_reason text,
 end_reason text,
 end_source text CHECK (end_source IN ('USER','SYSTEM')),
 office_revision integer,
 CHECK (end_time IS NULL OR end_time>=start_time)
);
CREATE UNIQUE INDEX one_open_session ON geoattend.work_sessions(day_id) WHERE end_time IS NULL;
CREATE TABLE geoattend.attendance_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 day_id uuid NOT NULL REFERENCES geoattend.attendance_days(id),
 session_id uuid REFERENCES geoattend.work_sessions(id),
 event_type text NOT NULL CHECK (event_type IN ('WORK_START','WORK_END','LUNCH_START','MORNING_LEAVE','FULL_DAY_LEAVE','LEAVE_CANCELLED','DAY_END')),
 event_time timestamptz NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT now(),
 source text NOT NULL CHECK (source IN ('USER','SYSTEM')),
 reason text,
 location_verified boolean
);
CREATE INDEX event_timeline ON geoattend.attendance_events(day_id,event_time);
CREATE TABLE geoattend.office_locations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 session_id uuid NOT NULL UNIQUE REFERENCES geoattend.work_sessions(id),
 start_event_id uuid NOT NULL UNIQUE REFERENCES geoattend.attendance_events(id),
 point geometry(Point,4326),
 accuracy_m double precision CHECK (accuracy_m>=0 AND accuracy_m<'Infinity'::float8),
 recorded_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL,
 purged_at timestamptz
);
CREATE INDEX location_point ON geoattend.office_locations USING gist(point);
CREATE INDEX location_expiry ON geoattend.office_locations(expires_at) WHERE purged_at IS NULL;
CREATE TABLE geoattend.attendance_requests (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES geoattend.profiles(id),
 request_id uuid NOT NULL,
 payload_hash text NOT NULL,
 result_event_ids uuid[] NOT NULL,
 completed_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(user_id,request_id)
);
