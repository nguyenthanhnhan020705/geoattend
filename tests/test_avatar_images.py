from io import BytesIO
import pytest
from PIL import Image
from app.accounts.avatar import validate_image
from app.errors import ApiError


@pytest.mark.parametrize('format,mime', [('JPEG','image/jpeg'),('PNG','image/png'),('WEBP','image/webp'),('GIF','image/gif')])
def test_supported_formats(format, mime):
    data = BytesIO()
    Image.new('RGB',(16,16),'blue').save(data,format=format)
    assert validate_image(data.getvalue()) == mime


def test_rejects_oversized_dimensions_and_svg():
    data = BytesIO()
    Image.new('RGB',(4097,1)).save(data,format='PNG')
    for content in (data.getvalue(),b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',b''):
        with pytest.raises(ApiError):
            validate_image(content)
