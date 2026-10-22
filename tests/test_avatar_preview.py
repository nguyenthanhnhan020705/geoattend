import pytest
import re
from playwright.sync_api import expect
from pathlib import Path
from tests.test_mobile_navigation_preview import preview


@pytest.mark.parametrize('width,pages', [(320,False),(1440,False),(390,True)])
def test_upload_avatar_and_reload(preview, width, pages):
    page, base = preview(width, pages=pages)
    saved = []
    gif = Path('app/static/images/avatars/default.gif').read_bytes()
    def avatar(route):
        if route.request.method == 'PUT':
            assert route.request.headers.get('x-csrf-token')
            if pages:
                assert route.request.headers.get('authorization', '').startswith('Bearer ')
            saved.append(route.request.post_data_buffer)
            route.fulfill(status=204)
        elif saved:
            route.fulfill(status=200,body=saved[-1],content_type='image/gif')
        else:
            route.fulfill(status=204)
    page.route('**/api/account/avatar', avatar)
    page.reload()
    page.locator('#avatar-file').set_input_files({'name':'cat.gif','mimeType':'image/gif','buffer':gif})
    expect(page.locator('#avatar-message')).to_contain_text('Đã cập nhật')
    assert saved == [gif]
    page.reload()
    expect(page.locator('#employee-avatar')).to_have_attribute('src', re.compile('^data:image/gif'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
