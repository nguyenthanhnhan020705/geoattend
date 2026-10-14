from uuid import UUID
from fastapi import APIRouter, Depends, Request, Response
from app.auth.dependencies import require_admin
from app.accounts.schemas import CreateUserInput, ResetPasswordInput
from app.accounts.service import create_user, list_users, reset_user_password
from app.clock import utc_now

router = APIRouter(prefix='/api/admin/users',dependencies=[Depends(require_admin)])


def public_account(account):
    return {'id':str(account.id),'username':account.username,'full_name':account.full_name,'role':account.role}


@router.get('')
def users(request: Request):
    with request.app.state.pool.connection() as conn:
        return {'items':[public_account(a) for a in list_users(conn)]}


@router.post('',status_code=201)
def create(body: CreateUserInput, request: Request):
    with request.app.state.pool.connection() as conn:
        return public_account(create_user(conn,body.username,body.full_name,body.password))


@router.post('/{account_id}/reset-password',status_code=204)
def reset(account_id: UUID, body: ResetPasswordInput, request: Request):
    with request.app.state.pool.connection() as conn:
        reset_user_password(conn,account_id,body.new_password,utc_now())
    return Response(status_code=204)
