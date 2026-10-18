from datetime import date
from uuid import UUID
from urllib.parse import quote, unquote
from fastapi import APIRouter, Depends, Header, Query, Request, Response
from starlette.concurrency import run_in_threadpool
from app.auth.dependencies import require_user, require_admin
from app.errors import ApiError
from app.reports import service
from app.reports.policy import MAX_PDF_BYTES, validate_pdf, validate_week

router = APIRouter(prefix='/api/weekly-reports', dependencies=[Depends(require_user)])
admin_router = APIRouter(prefix='/api/admin/weekly-reports', dependencies=[Depends(require_admin)])


def call_service(request, function, *args):
    with request.app.state.pool.connection() as conn:
        return function(conn, request.state.auth, *args)


@router.get('/status')
def status(request: Request):
    return call_service(request, service.status)


@router.get('')
def own(request: Request, page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=100)):
    return call_service(request, service.list_own, page, page_size)


@router.put('/{week_start}')
async def upload(week_start: date, request: Request, request_id: UUID, expected_revision: int=Query(ge=0),
                 filename: str=Header(alias='X-Report-Filename',min_length=5,max_length=2500)):
    validate_week(week_start)
    try:
        filename=unquote(filename,encoding='utf-8',errors='strict')
    except UnicodeError:
        raise ApiError(422,'INVALID_INPUT','Tên file không hợp lệ.')
    length = request.headers.get('content-length')
    if length:
        try:
            length = int(length)
        except ValueError:
            raise ApiError(422,'INVALID_INPUT','Dung lượng file không hợp lệ.')
        if length < 0:
            raise ApiError(422,'INVALID_INPUT','Dung lượng file không hợp lệ.')
        if length > MAX_PDF_BYTES:
            raise ApiError(413,'REPORT_TOO_LARGE','File PDF tối đa 10 MB.')
    content = bytearray()
    async for chunk in request.stream():
        if len(content)+len(chunk) > MAX_PDF_BYTES:
            raise ApiError(413,'REPORT_TOO_LARGE','File PDF tối đa 10 MB.')
        content.extend(chunk)
    pdf = bytes(content)
    name = validate_pdf(filename,request.headers.get('content-type',''),pdf)
    return await run_in_threadpool(call_service,request,service.submit,week_start,request_id,expected_revision,name,pdf)


def pdf_response(row, download):
    disposition = 'attachment' if download else 'inline'
    return Response(bytes(row['pdf']),media_type='application/pdf',headers={
        'Content-Disposition':disposition+"; filename=weekly-report.pdf; filename*=UTF-8''"+quote(row['filename'],safe=''),
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
    })


@router.get('/{report_id}/file')
def own_file(report_id: UUID, request: Request, download: bool=False):
    return pdf_response(call_service(request,service.read_file,report_id),download)


@admin_router.get('')
def admin_list(request: Request, week_start: date | None=None, user_id: UUID | None=None,
               page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=100)):
    return call_service(request,service.list_admin,week_start,user_id,page,page_size)


@admin_router.get('/{report_id}/file')
def admin_file(report_id: UUID, request: Request, download: bool=False):
    return pdf_response(call_service(request,service.read_file,report_id,True),download)
