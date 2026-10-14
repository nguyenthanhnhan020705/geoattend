from datetime import date
from fastapi import APIRouter, Depends, Query, Request
from app.auth.dependencies import require_user
from app.attendance.schemas import ActionInput
from app.attendance import service
from app.errors import ApiError

router = APIRouter(prefix='/api/attendance',dependencies=[Depends(require_user)])


@router.get('/status')
def status(request: Request):
    with request.app.state.pool.connection() as conn:
        return service.status(conn,request.state.auth.account.id)


@router.post('/actions')
def act(body: ActionInput, request: Request):
    with request.app.state.pool.connection() as conn:
        return service.act(conn,request.state.auth.account.id,body)


@router.get('/history')
def history(request: Request, start: date | None = Query(None,alias='from'), end: date | None = Query(None,alias='to'), page: int = Query(1,ge=1), page_size: int = Query(20,ge=1,le=100)):
    if set(request.query_params)-{'from','to','page','page_size'}:
        raise ApiError(422,'INVALID_INPUT','Tham số lịch sử không hợp lệ.')
    with request.app.state.pool.connection() as conn:
        return service.history(conn,request.state.auth.account.id,start,end,page,page_size)
