from fastapi import APIRouter, Depends, Request, Response
from app.auth.dependencies import get_auth_context, validate_origin
from app.auth.schemas import LoginInput
from app.auth.service import login, SESSION_TTL_SECONDS
from app.auth.repository import revoke_session
from app.clock import utc_now
from app.errors import ApiError

router = APIRouter(prefix='/api/auth')


def account_response(context):
    a = context.account
    return {'id':str(a.id),'username':a.username,'full_name':a.full_name,'role':a.role,'csrf_token':context.csrf_token}


@router.post('/login')
def login_route(body: LoginInput, request: Request, response: Response):
    validate_origin(request,request.app.state.settings.origin)
    if not request.headers.get('content-type','').startswith('application/json'):
        raise ApiError(422,'INVALID_INPUT','Đăng nhập yêu cầu JSON.')
    if request.app.state.pool is None:
        raise ApiError(503,'DATABASE_UNAVAILABLE','Cơ sở dữ liệu chưa sẵn sàng.')
    with request.app.state.pool.connection() as conn:
        result = login(conn,body.username,body.password,utc_now())
    response.set_cookie('geoattend_session',result.raw_token,max_age=SESSION_TTL_SECONDS,httponly=True,secure=request.app.state.settings.secure_cookies,samesite='lax',path='/')
    return account_response(result)


@router.get('/me')
def me(context=Depends(get_auth_context)):
    return account_response(context)


@router.post('/logout',status_code=204)
def logout(request: Request, context=Depends(get_auth_context)):
    with request.app.state.pool.connection() as conn:
        revoke_session(conn,context.session_id,utc_now())
    response = Response(status_code=204)
    response.delete_cookie('geoattend_session',path='/')
    return response
