"""Build an allowlisted, secret-free frontend. No backend dependencies required."""
import argparse
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'app/static'
ROUTES = {
    'login': 'login.html', 'user': 'user.html', 'account': 'account.html',
    'admin/users': 'admin-users.html', 'admin/dashboard': 'admin-dashboard.html',
    'admin/office': 'admin-office.html', 'user/weekly-reports': 'user-weekly-reports.html',
    'admin/weekly-reports': 'admin-weekly-reports.html',
}


def validate_origin(value, *, allow_loopback=False):
    if not value:
        return ''
    parsed = urlsplit(value)
    # Require a literal origin, not an arbitrary URL, header or HTML fragment.
    if (not re.fullmatch(r'https?://[A-Za-z0-9.-]+(?::[0-9]+)?', value)
            or not parsed.hostname or parsed.path or parsed.username
            or not 0 < (parsed.port or 443) < 65536
            or (parsed.scheme != 'https' and not (allow_loopback and parsed.hostname in ('localhost', '127.0.0.1')))):
        raise ValueError('API origin must be an HTTPS origin without path or credentials.')
    return value


def build_pages(output: Path, *, base_path: str, api_origin: str, version: str,
                allow_loopback: bool = False) -> None:
    api_origin = validate_origin(api_origin, allow_loopback=allow_loopback)
    if not re.fullmatch(r'/(?:[A-Za-z0-9_-]+/)*', base_path):
        raise ValueError('Base path must be / or /repository/.')
    output = Path(output).resolve()
    if (output == ROOT or output == SOURCE or output in SOURCE.parents
            or SOURCE in output.parents or (output.exists() and any(output.iterdir()))):
        raise ValueError('Use a new, empty artifact directory outside the source.')
    output.mkdir(parents=True, exist_ok=True)
    extensions = {'.css', '.js', '.jpg', '.jpeg', '.png', '.svg', '.webp', '.woff', '.woff2', '.txt'}
    for folder in ('css', 'js', 'images', 'vendor'):
        for asset in (SOURCE / folder).rglob('*'):
            if asset.is_symlink():
                raise ValueError('Symlink assets are not permitted.')
            if asset.is_file() and (asset.suffix.lower() in extensions or asset.name.startswith('LICENSE')):
                target = output / 'static' / asset.relative_to(SOURCE)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(asset, target)
    config = dict(mode='pages', basePath=base_path, apiOrigin=api_origin, version=version)
    (output / 'static/js/runtime-config.js').write_text(
        'export const runtimeConfig = ' + json.dumps(config, ensure_ascii=True) + ';\n', encoding='utf-8')
    maps = 'https://tiles.openfreemap.org https://tile.openstreetmap.org'
    csp = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
           f"img-src 'self' data: blob: {maps}; connect-src 'self' {api_origin} {maps}; "
           "worker-src 'self' blob:; frame-src blob:; object-src 'none'; base-uri 'none'; form-action 'none'")
    security = ('<meta http-equiv="Content-Security-Policy" content="' + html.escape(csp, quote=True)
                + '"><meta name="referrer" content="no-referrer">')

    def rewrite(match):
        attr, quote, url = match.groups()
        if url.startswith('/static/'):
            url = base_path + url[1:]
        elif url.lstrip('/') in ROUTES:
            url = base_path + url.lstrip('/') + '/'
        return f'{attr}={quote}{url}{quote}'

    for route, filename in ROUTES.items():
        content = (SOURCE / filename).read_text(encoding='utf-8-sig')
        content = re.sub(r'(href|src)=([\"\'])(.*?)\2', rewrite, content)
        content = content.replace('<head>', '<head>' + security, 1)
        if route != 'login':
            content = content.replace('<body', '<body data-session-pending', 1)
        target = output / route / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    # Reuse login at the root; no inline script or refresh redirect is necessary.
    shutil.copyfile(output / 'login/index.html', output / 'index.html')
    (output / '.nojekyll').touch()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base-path', default='/geoattend/')
    parser.add_argument('--api-origin', default='')
    parser.add_argument('--version', default='local')
    args = parser.parse_args()
    build_pages(args.output, base_path=args.base_path, api_origin=args.api_origin, version=args.version)


if __name__ == '__main__':
    main()
