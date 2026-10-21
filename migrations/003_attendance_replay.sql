-- No GPS/payload copy: only the original non-sensitive action result.
ALTER TABLE geoattend.attendance_requests
 ADD COLUMN result_status text,
 ADD COLUMN result_revision integer,
 ADD COLUMN result_work_date date,
 ADD COLUMN result_session_id uuid REFERENCES geoattend.work_sessions(id);
CREATE INDEX attendance_due_days ON geoattend.attendance_days(work_date,user_id)
 WHERE status IN ('WORKING_OFFICE','WORKING_REMOTE','LUNCH_BREAK');
