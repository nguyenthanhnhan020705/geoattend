from fastapi import APIRouter,Depends,Request
from app.auth.dependencies import require_admin
from app.gis.schemas import OfficeInput
from app.gis.service import get_office,save_office

router=APIRouter(prefix='/api/admin/office',dependencies=[Depends(require_admin)])


@router.get('')
def get(request: Request):
    with request.app.state.pool.connection() as conn:
        result=get_office(conn)
        settings=request.app.state.settings
        result['map']={'mode':settings.map_kind,'tile_url':settings.map_tile_url,'attribution':settings.map_attribution,'style_url':settings.map_style_url}
        return result


@router.put('')
def save(body: OfficeInput,request: Request):
    with request.app.state.pool.connection() as conn:
        return save_office(conn,body,request.state.auth)
