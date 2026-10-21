from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, Query, Request, Response
from app.auth.dependencies import require_admin
from app.accounts.schemas import CreateUserInput, ResetPasswordInput, DeleteHistoryInput
from app.accounts import history_service
from app.errors import ApiError
from app.accounts.service import create_user, list_users, reset_user_password
from app.clock import utc_now
from app import clock
from app.attendance.service import VIETNAM

router = APIRouter(prefix='/api/admin/users',dependencies=[Depends(require_admin)])


def public_account(account):
    return {'id':str(account.id),'username':account.username,'full_name':account.full_name,'role':account.role}


@router.get('')
def users(request: Request):
    with request.app.state.pool.connection() as conn:
        return {'items':[public_account(a) for a in list_users(conn)],
                'work_date':clock.utc_now().astimezone(VIETNAM).date().isoformat()}


@router.post('',status_code=201)
def create(body: CreateUserInput, request: Request):
    with request.app.state.pool.connection() as conn:
        return public_account(create_user(conn,body.username,body.full_name,body.password))


@router.post('/{account_id}/reset-password',status_code=204)
def reset(account_id: UUID, body: ResetPasswordInput, request: Request):
    with request.app.state.pool.connection() as conn:
        reset_user_password(conn,account_id,body.new_password,utc_now())
    return Response(status_code=204)


@router.get('/{account_id}/history')
def history(account_id: UUID, request: Request, start: date | None = Query(None,alias='from'), end: date | None = Query(None,alias='to'), page: int = Query(1,ge=1), page_size: int = Query(20,ge=1,le=100)):
    if set(request.query_params)-{'from','to','page','page_size'}:
        raise ApiError(422,'INVALID_INPUT','Tham số lịch sử không hợp lệ.')
    with request.app.state.pool.connection() as conn:
        return history_service.history(conn,request.state.auth,account_id,start,end,page,page_size)


@router.delete('/{account_id}/history/{day_id}')
def delete_history(account_id: UUID, day_id: UUID, body: DeleteHistoryInput, request: Request):
    with request.app.state.pool.connection() as conn:
        return history_service.delete_day(conn,request.state.auth,account_id,day_id,body)
