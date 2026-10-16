from fastapi import APIRouter, Depends, Request
from app.auth.dependencies import require_admin
from app.admin.schemas import Dashboard, Onsite
from app.admin.service import build_snapshot

router = APIRouter(prefix='/api/admin',dependencies=[Depends(require_admin)])


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
