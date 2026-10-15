-- Only technical concurrency/retry markers survive permanent history deletion.
-- No session, reason, event or GPS payload is retained by these markers.
ALTER TABLE geoattend.attendance_days
 ADD COLUMN history_deleted boolean NOT NULL DEFAULT false;
ALTER TABLE geoattend.attendance_requests
 ADD COLUMN history_deleted boolean NOT NULL DEFAULT false;
