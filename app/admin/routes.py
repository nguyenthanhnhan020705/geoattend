from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, Response
from app.auth.dependencies import require_admin
from app.admin.schemas import Dashboard, Onsite
from app.admin.service import build_snapshot
from app.admin.export import export_attendance
from app.errors import ApiError

router = APIRouter(prefix='/api/admin',dependencies=[Depends(require_admin)])


@router.get('/attendance/export')
def attendance_export(request: Request, start: date | None=Query(None, alias='from'),
                      end: date | None=Query(None, alias='to'), user_id: UUID | None=None):
    if set(request.query_params)-{'from','to','user_id'}:
        raise ApiError(422, 'INVALID_INPUT', 'Bộ lọc xuất Excel không hợp lệ.')
    with request.app.state.pool.connection() as conn:
        content, filename = export_attendance(conn, request.state.auth, start, end, user_id)
    return Response(content, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"', 'Cache-Control': 'no-store'})


@router.get('/dashboard',response_model=Dashboard)
def dashboard(request: Request):
    with request.app.state.pool.connection() as conn:
        data=build_snapshot(conn,request.state.auth)
    settings=request.app.state.settings
    data['office']['map']={'mode':settings.map_kind,'tile_url':settings.map_tile_url,'attribution':settings.map_attribution,'style_url':settings.map_style_url}
    return data


@router.get('/onsite',response_model=Onsite)
def onsite(request: Request):
    data=dashboard(request)
    return dict(as_of=data['as_of'],work_date=data['work_date'],items=data['onsite'],office=data['office'])
