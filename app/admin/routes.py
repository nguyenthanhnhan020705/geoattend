from fastapi import APIRouter, Depends, Request
from app.auth.dependencies import require_admin
from app.admin.schemas import Dashboard
from app.admin.service import build_snapshot

router = APIRouter(prefix='/api/admin',dependencies=[Depends(require_admin)])


@router.get('/dashboard',response_model=Dashboard)
def dashboard(request: Request):
    with request.app.state.pool.connection() as conn:
        return build_snapshot(conn,request.state.auth)
