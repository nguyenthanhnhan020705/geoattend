from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

import pytest


def build(tmp_path, **kw):
    from scripts.build_pages import build_pages
    output = tmp_path / 'site'
    build_pages(output, base_path=kw.pop('base_path', '/geoattend/'),
                api_origin=kw.pop('api_origin', ''), version='test', **kw)
    return output


@pytest.mark.parametrize('base', ['/geoattend/', '/'])
def test_artifact_routes_assets_and_no_private_files(tmp_path, base):
    output = build(tmp_path, base_path=base)
    routes = ['login', 'user', 'account', 'admin/users', 'admin/dashboard',
              'admin/office', 'user/weekly-reports', 'admin/weekly-reports']
    for route in routes:
        assert (output / route / 'index.html').is_file()
    assert (output / 'index.html').is_file()
    assert (output / '.nojekyll').is_file()
    class Assets(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            for key in ('href', 'src'):
                url = attrs.get(key, '')
                if url.startswith(base):
                    target = output / unquote(urlsplit(url).path[len(base):])
                    assert target.exists(), url
    for page in output.rglob('*.html'):
        html = page.read_text(encoding='utf-8')
        Assets().feed(html)
        assert 'Content-Security-Policy' in html
        assert 'no-referrer' in html
    assert not any(p.suffix in {'.py', '.sql', '.env', '.dump'} for p in output.rglob('*'))
    config = (output / 'static/js/runtime-config.js').read_text(encoding='utf-8')
    assert 'pages' in config and base in config
    assert 'CHANGE_ME' not in config


@pytest.mark.parametrize('api', ['http://evil.test', 'https://a.test/x', 'https://u:p@a.test',
                                    'https://a.test?x=1', 'https://a.test/#x', 'javascript:alert(1)',
                                    'https://a.test;bad', 'https://a.test\\evil'])
def test_invalid_api_origin_refused(tmp_path, api):
    with pytest.raises(ValueError):
        build(tmp_path, api_origin=api)


@pytest.mark.parametrize('base', ['../', '/a/../', '/a?x=1/', '/a"/'])
def test_invalid_base_path_refused(tmp_path, base):
    with pytest.raises(ValueError):
        build(tmp_path, base_path=base)


def test_https_origin_and_csp(tmp_path):
    output = build(tmp_path, api_origin='https://api.example.com')
    html = (output / 'login/index.html').read_text(encoding='utf-8')
    assert 'https://api.example.com' in html
    assert html.index('Content-Security-Policy') < html.index('stylesheet')
    assert "object-src 'none'" in unescape(html)


def test_refuse_output_that_contains_source():
    from scripts.build_pages import build_pages
    with pytest.raises(ValueError):
        build_pages(Path.cwd(), base_path='/geoattend/', api_origin='', version='test')


def test_loopback_is_explicit(tmp_path):
    with pytest.raises(ValueError):
        build(tmp_path, api_origin='http://127.0.0.1:8000')
    build(tmp_path, api_origin='http://127.0.0.1:8000', allow_loopback=True)
