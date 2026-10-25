from contextlib import asynccontextmanager
from pathlib import Path
import psycopg
from psycopg_pool import PoolTimeout
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from app.config import Settings
from app.errors import ApiError
from app.db.pool import make_pool
from app.auth.routes import router as auth_router
from app.accounts.routes import router as accounts_router
from app.accounts.avatar import router as avatar_router
from app.attendance.routes import router as attendance_router
from app.gis.routes import router as office_router
from app.admin.routes import router as admin_router
from app.auth.dependencies import get_auth_context
from app.telemetry import ApiTiming
from app.reports.routes import router as reports_router, admin_router as admin_reports_router
from app.reports.summary_routes import router as summaries_router, admin_router as admin_summaries_router

STATIC = Path(__file__).parent / 'static'


class TimedFastAPI(FastAPI):
    async def __call__(self,scope,receive,send):
        # FastAPI's outer ServerErrorMiddleware generates unhandled 500 bodies.
        # Timing must surround that entire stack, not live inside add_middleware.
        application = super().__call__
        if self.state.settings.frontend_origin:
            # Outside ServerErrorMiddleware, so error responses also have CORS.
            application = CORSMiddleware(application,
                allow_origins=[self.state.settings.frontend_origin],
                allow_methods=['GET','POST','PUT','DELETE'],
                allow_headers=['Authorization','Content-Type','X-CSRF-Token','X-Report-Filename'],
                allow_credentials=False)
        await ApiTiming(application)(scope,receive,send)


def create_app(settings=None, pool=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        owned = pool is None and bool(settings.database_url)
        app.state.pool = pool or (make_pool(settings.database_url) if owned else None)
        if owned:
            app.state.pool.open()
        yield
        if owned:
            app.state.pool.close()

    app = TimedFastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.include_router(auth_router)
    app.include_router(accounts_router)
    app.include_router(avatar_router)
    app.include_router(attendance_router)
    app.include_router(office_router)
    app.include_router(admin_router)
    app.include_router(reports_router)
    app.include_router(admin_reports_router)
    app.include_router(summaries_router)
    app.include_router(admin_summaries_router)

    @app.middleware('http')
    async def auth_cache(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(('/api/auth','/api/admin','/api/attendance','/api/weekly-reports')):
            response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        if request.url.path in ('/admin/office','/admin/dashboard'):
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: "+settings.map_tile_origin+' '+settings.map_style_origin+"; connect-src 'self' "+settings.map_style_origin+"; worker-src 'self' blob:; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        return response

    @app.exception_handler(ApiError)
    async def api_error(request, error):
        return JSONResponse({'code': error.code, 'message': error.message}, status_code=error.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return JSONResponse({'code': 'INVALID_INPUT', 'message': 'Thông tin nhập không hợp lệ.'}, status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return JSONResponse({'code': 'HTTP_ERROR', 'message': 'Không tìm thấy hoặc không thể truy cập.'}, status_code=error.status_code)

    async def database_error(request, error):
        return JSONResponse({'code': 'DATABASE_UNAVAILABLE', 'message': 'Cơ sở dữ liệu chưa sẵn sàng.'}, status_code=503)

    app.add_exception_handler(psycopg.OperationalError, database_error)
    app.add_exception_handler(PoolTimeout, database_error)

    @app.get('/api/health')
    def health():
        if app.state.pool is None:
            raise ApiError(503, 'DATABASE_UNAVAILABLE', 'Cơ sở dữ liệu chưa sẵn sàng.')
        with app.state.pool.connection() as conn:
            conn.execute('SELECT 1').fetchone()
        return {'status': 'ok', 'database': 'ok'}

    @app.get('/login', include_in_schema=False)
    def login_page():
        return FileResponse(STATIC / 'login.html', media_type='text/html')

    def protected_page(request, filename, role=None):
        try:
            context = get_auth_context(request)
        except ApiError as error:
            if error.status_code == 401:
                return RedirectResponse('/login',status_code=303)
            raise
        if role and context.account.role != role:
            raise ApiError(403,'FORBIDDEN','Bạn không có quyền truy cập trang này.')
        return FileResponse(STATIC/filename, media_type='text/html',headers={'Cache-Control':'no-store'})

    @app.get('/',include_in_schema=False)
    def index():
        return RedirectResponse('/login',status_code=303)

    @app.get('/user',include_in_schema=False)
    def user_page(request: Request):
        return protected_page(request,'user.html','USER')

    @app.get('/admin/users',include_in_schema=False)
    def admin_users_page(request: Request):
        return protected_page(request,'admin-users.html','ADMIN')

    @app.get('/admin/dashboard',include_in_schema=False)
    def admin_dashboard_page(request: Request):
        return protected_page(request,'admin-dashboard.html','ADMIN')

    @app.get('/account',include_in_schema=False)
    def account_page(request: Request):
        return protected_page(request,'account.html')

    @app.get('/user/weekly-reports',include_in_schema=False)
    def user_reports_page(request: Request):
        return protected_page(request,'user-weekly-reports.html','USER')

    @app.get('/admin/weekly-reports',include_in_schema=False)
    def admin_reports_page(request: Request):
        return protected_page(request,'admin-weekly-reports.html','ADMIN')

    @app.get('/admin/office',include_in_schema=False)
    def office_page(request: Request):
        return protected_page(request,'admin-office.html','ADMIN')

    app.mount('/static', StaticFiles(directory=STATIC), name='static')
    return app


app = create_app()
