"""Personal avatars, stored with the account rather than ephemeral server files."""
from io import BytesIO
import warnings
from fastapi import APIRouter, Depends, Request, Response
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from app.auth.dependencies import require_user
from app.reports.service import authorize
from app.errors import ApiError

MAX_BYTES = 5_000_000
TYPES = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp', 'GIF': 'image/gif'}
router = APIRouter(prefix='/api/account/avatar', dependencies=[Depends(require_user)])


def validate_image(content):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                media_type = TYPES.get(image.format)
                if not media_type or max(image.size) > 4096:
                    raise ValueError('format or dimensions')
                pixels = 0
                frame = 0
                while True:
                    pixels += image.width * image.height
                    if pixels > 80_000_000:
                        raise ValueError('decoded image too large')
                    image.load()
                    frame += 1
                    try:
                        image.seek(frame)
                    except EOFError:
                        break
                return media_type
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ApiError(422, 'INVALID_AVATAR', 'Chọn ảnh JPG, PNG, WebP hoặc GIF hợp lệ; kích thước tối đa 4096 × 4096 và ảnh động không quá dài.')


def stored_avatar(request, content=None):
    with request.app.state.pool.connection() as conn:
        with conn.transaction():
            authorize(conn, request.state.auth)
            if content is not None:
                media_type = validate_image(content)
                conn.execute('INSERT INTO geoattend.user_avatars(user_id,content,media_type) VALUES(%s,%s,%s) '
                             'ON CONFLICT(user_id) DO UPDATE SET content=EXCLUDED.content,media_type=EXCLUDED.media_type',
                             (request.state.auth.account.id, content, media_type))
                return Response(status_code=204, headers={'Cache-Control': 'no-store'})
            row = conn.execute('SELECT content,media_type FROM geoattend.user_avatars WHERE user_id=%s',
                               (request.state.auth.account.id,)).fetchone()
            if row is None:
                return Response(status_code=204, headers={'Cache-Control': 'no-store'})
            return Response(bytes(row['content']), media_type=row['media_type'], headers={'Cache-Control': 'no-store'})


@router.get('')
def read(request: Request):
    return stored_avatar(request)


@router.put('')
async def upload(request: Request):
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_BYTES:
            raise ApiError(413, 'AVATAR_TOO_LARGE', 'Ảnh đại diện tối đa 5 MB.')
        content.extend(chunk)
    return await run_in_threadpool(stored_avatar, request, bytes(content))
