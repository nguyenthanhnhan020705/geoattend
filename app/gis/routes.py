from fastapi import APIRouter,Depends,Request
from app.auth.dependencies import require_admin
from app.gis.schemas import OfficeInput
from app.gis.service import get_office,save_office

router=APIRouter(prefix='/api/admin/office',dependencies=[Depends(require_admin)])


@router.get('')
def get(request: Request):
    with request.app.state.pool.connection() as conn:
        return get_office(conn)


@router.put('')
def save(body: OfficeInput,request: Request):
    with request.app.state.pool.connection() as conn:
        return save_office(conn,body,request.state.auth)
