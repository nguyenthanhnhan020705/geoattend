"""Fail clearly before reading a PDF when reporting schema/grants are absent."""
from app.errors import ApiError
from fastapi import Request


def require_reports_ready(request: Request):
    with request.app.state.pool.connection() as conn:
        ready=conn.execute("""WITH objects AS (
            SELECT to_regclass('geoattend.weekly_reports') AS reports,
                   to_regclass('geoattend.schema_migrations') AS ledger
        ) SELECT reports IS NOT NULL AND ledger IS NOT NULL
            AND has_table_privilege(current_user,reports,'SELECT')
            AND has_table_privilege(current_user,reports,'INSERT')
            AND has_table_privilege(current_user,reports,'UPDATE')
            AND has_column_privilege(current_user,ledger,'name','SELECT')
            AND has_column_privilege(current_user,ledger,'applied_at','SELECT') AS ready
            FROM objects""").fetchone()['ready']
        if ready:
            ready=bool(conn.execute("SELECT 1 FROM geoattend.schema_migrations WHERE name='005_weekly_reports.sql'").fetchone())
    if not ready:
        raise ApiError(503,'REPORTS_NOT_READY',
                       'Chức năng báo cáo tuần chưa được kích hoạt trên hệ thống. Vui lòng liên hệ người quản trị.')
