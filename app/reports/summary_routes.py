"""Private summary endpoints, isolated from upload and file readiness."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from app.auth.dependencies import require_admin
from app.errors import ApiError
from app.reports.service import authorize
from app.reports.summaries import ready

# Retain the original URL as an Admin-only alias; User cannot read or retry.
router = APIRouter(prefix='/api/weekly-reports',dependencies=[Depends(require_admin)])
admin_router = APIRouter(prefix='/api/admin/weekly-reports',dependencies=[Depends(require_admin)])

MESSAGES = {
    'UNREADABLE':'Không thể đọc nội dung tài liệu để tóm tắt',
    'PDF_PASSWORD':'PDF được bảo vệ bằng mật khẩu, không thể tóm tắt.',
    'PAGE_LIMIT':'PDF vượt giới hạn 1.000 trang của dịch vụ tóm tắt.',
    'RATE_LIMIT':'Dịch vụ AI đang hết hạn mức. Vui lòng thử lại sau.',
    'AI_TIMEOUT':'Tạo bản tóm tắt quá thời gian chờ. Bạn có thể thử lại.',
    'UNCERTAIN_RESULT':'Lần xử lý trước bị gián đoạn. Tạo lại có thể phát sinh thêm chi phí AI.',
    'PROVIDER_AUTH':'Dịch vụ tóm tắt chưa được cấu hình hợp lệ. Vui lòng liên hệ Admin.',
}


def summary_response(conn, context, report_id, revision, *, admin=False, retry=False):
    with conn.transaction():
        authorize(conn,context,admin=admin)
        if not ready(conn):
            raise ApiError(503,'SUMMARY_UNAVAILABLE','Chức năng tóm tắt chưa sẵn sàng. Bạn vẫn có thể xem và tải PDF.')
        report = conn.execute("SELECT r.id,r.revision,r.content_sha256 FROM geoattend.weekly_reports r "
                              "JOIN geoattend.profiles p ON p.id=r.user_id WHERE r.id=%s AND p.role='USER'"+
                              ('' if admin else ' AND r.user_id=%s')+' FOR SHARE OF r',
                              (report_id,) if admin else (report_id,context.account.id)).fetchone()
        if report is None:
            raise ApiError(404,'REPORT_NOT_FOUND','Không tìm thấy báo cáo.')
        if report['revision']!=revision:
            raise ApiError(409,'STALE_REVISION','PDF đã được thay thế. Vui lòng tải lại danh sách báo cáo.')
        args=(report_id,report['content_sha256'])
        if retry:
            row=conn.execute("""UPDATE geoattend.pdf_summaries SET status='PENDING',summary=NULL,
                error_code=NULL,lease_token=NULL,lease_expires_at=NULL,updated_at=now()
                WHERE report_id=%s AND content_sha256=%s AND status='FAILED' AND attempt_count<3
                RETURNING status,summary,error_code,attempt_count""",args).fetchone()
            if row is None:
                raise ApiError(409,'SUMMARY_NOT_RETRYABLE','Bản tóm tắt đang xử lý, đã hoàn tất hoặc đã hết số lần thử. Vui lòng tải lại trạng thái.')
        else:
            row=conn.execute('SELECT status,summary,error_code,attempt_count FROM geoattend.pdf_summaries WHERE report_id=%s AND content_sha256=%s',args).fetchone()
        state=row['status'] if row else 'NOT_CREATED'
        error=row['error_code'] if row else None
        message=('Chưa tạo bản tóm tắt. Đang chờ tiến trình xử lý.' if state=='NOT_CREATED'
                 else 'Đang tạo bản tóm tắt...' if state in ('PENDING','PROCESSING')
                 else MESSAGES.get(error,'Không thể tạo bản tóm tắt. Vui lòng thử lại sau.') if state=='FAILED'
                 else '')
        return dict(status=state,summary=row['summary'] if row else None,error_code=error,
                    message=message,revision=revision,can_retry=bool(row and state=='FAILED' and row['attempt_count']<3))


def call(request, report_id, revision, admin=False, retry=False):
    with request.app.state.pool.connection() as conn:
        return summary_response(conn,request.state.auth,report_id,revision,admin=admin,retry=retry)


@router.get('/{report_id}/summary')
def own(report_id: UUID, request: Request, expected_revision: int=Query(ge=1)):
    return call(request,report_id,expected_revision,admin=True)


@router.post('/{report_id}/summary')
def retry_own(report_id: UUID, request: Request, expected_revision: int=Query(ge=1)):
    return call(request,report_id,expected_revision,admin=True,retry=True)


@admin_router.get('/{report_id}/summary')
def other(report_id: UUID, request: Request, expected_revision: int=Query(ge=1)):
    return call(request,report_id,expected_revision,admin=True)


@admin_router.post('/{report_id}/summary')
def retry_other(report_id: UUID, request: Request, expected_revision: int=Query(ge=1)):
    return call(request,report_id,expected_revision,admin=True,retry=True)
