import secrets
from fastapi import Request
from app.clock import utc_now
from app.auth.service import resolve_session
from app.errors import ApiError


def validate_origin(request, origin):
    supplied = request.headers.get('origin')
    if supplied is not None and supplied != origin:
        raise ApiError(403,'INVALID_ORIGIN','Nguồn yêu cầu không hợp lệ.')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise ApiError(403,'INVALID_ORIGIN','Nguồn yêu cầu không hợp lệ.')


def validate_csrf(request, context):
    validate_origin(request,request.app.state.settings.origin)
    token = request.headers.get('x-csrf-token','')
    if not secrets.compare_digest(token,context.csrf_token):
        raise ApiError(403,'INVALID_CSRF','Yêu cầu không hợp lệ. Vui lòng tải lại trang.')


def get_auth_context(request: Request):
    if getattr(request.state,'auth',None):
        return request.state.auth
    if request.app.state.pool is None:
        raise ApiError(503,'DATABASE_UNAVAILABLE','Cơ sở dữ liệu chưa sẵn sàng.')
    with request.app.state.pool.connection() as conn:
        context = resolve_session(conn,request.cookies.get('geoattend_session',''),utc_now())
    request.state.auth = context
    if request.method not in ('GET','HEAD','OPTIONS'):
        validate_csrf(request,context)
    return context


def require_admin(request: Request):
    context = get_auth_context(request)
    if context.account.role != 'ADMIN':
        raise ApiError(403,'FORBIDDEN','Chức năng dành cho Admin.')
    return context


def require_user(request: Request):
    context = get_auth_context(request)
    if context.account.role != 'USER':
        raise ApiError(403,'FORBIDDEN','Chức năng chấm công dành cho User.')
    return context
