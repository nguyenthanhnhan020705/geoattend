"""Standard-library checks also run in GitHub Actions without backend packages."""
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

from scripts.build_pages import build_pages, ROUTES


class PagesArtifactTests(unittest.TestCase):
    def test_public_artifact_routes_and_local_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'site'
            build_pages(output,base_path='/geoattend/',api_origin='',version='ci')
            for path in ['',*ROUTES]:
                self.assertTrue((output/path/'index.html').is_file(),path)
            class Links(HTMLParser):
                def handle_starttag(parser, tag, attributes):
                    for key,url in attributes:
                        if key in ('href','src') and url and url.startswith('/geoattend/'):
                            self.assertTrue((output/unquote(urlsplit(url).path.removeprefix('/geoattend/'))).exists(),url)
            for path in output.rglob('*.html'):
                Links().feed(path.read_text(encoding='utf-8'))
            for path in output.rglob('*.js'):
                for ref in re.findall(r"(?:from\s*|import\s*)['\"](\.[^'\"]+)['\"]",path.read_text(encoding='utf-8')):
                    self.assertTrue((path.parent/unquote(urlsplit(ref).path)).is_file(),f'{path.name}: {ref}')
            # Product CSS image dependencies; library defaults are maintained upstream.
            for path in (output/'static/css').glob('*.css'):
                for ref in re.findall(r'url\([\"\']?([^\)\"\']+)',path.read_text(encoding='utf-8')):
                    if not ref.startswith(('https:','data:','#')):
                        self.assertTrue((path.parent/ref).is_file(),f'{path.name}: {ref}')
            self.assertTrue(all(p.suffix not in ('.py','.sql','.env','.dump') for p in output.rglob('*')))


if __name__=='__main__':
    unittest.main()
