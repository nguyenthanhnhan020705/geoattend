import os
from urllib.parse import urlsplit
from dataclasses import dataclass
from string import Formatter


@dataclass(frozen=True)
class Settings:
    database_url: str = ''
    migration_database_url: str = ''
    origin: str = 'http://127.0.0.1:8000'
    secure_cookies: bool = False
    map_tile_url: str = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
    map_attribution: str = '© OpenStreetMap contributors'

    def __post_init__(self):
        parsed = urlsplit(self.origin)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('GEOATTEND_ORIGIN phải là scheme/host/port.')
        if parsed.scheme == 'https' and not self.secure_cookies:
            raise ValueError('HTTPS yêu cầu cookie Secure.')
        tile=urlsplit(self.map_tile_url)
        fields={name for _,name,_,_ in Formatter().parse(self.map_tile_url) if name is not None}
        if not tile.hostname or tile.username or tile.password or tile.fragment or any(c.isspace() for c in self.map_tile_url) or fields!={'z','x','y'}:
            raise ValueError('URL bản đồ phải có host và {z}/{x}/{y}, không chứa thông tin đăng nhập.')
        if tile.scheme!='https' and not (tile.scheme=='http' and tile.hostname in ('localhost','127.0.0.1')):
            raise ValueError('Bản đồ yêu cầu HTTPS hoặc localhost.')
        if not self.map_attribution.strip() or len(self.map_attribution)>1000:
            raise ValueError('Thiếu thông tin nguồn bản đồ.')

    @property
    def map_tile_origin(self):
        parsed=urlsplit(self.map_tile_url)
        return parsed.scheme+'://'+parsed.netloc


    @classmethod
    def from_env(cls):
        origin = os.getenv('GEOATTEND_ORIGIN', 'http://127.0.0.1:8000')
        secure = os.getenv('GEOATTEND_SECURE_COOKIES', str(origin.startswith('https://'))).lower()
        if secure not in ('true', 'false'):
            raise ValueError('GEOATTEND_SECURE_COOKIES phải là true hoặc false.')
        return cls(os.getenv('GEOATTEND_DATABASE_URL', ''), os.getenv('GEOATTEND_MIGRATION_DATABASE_URL', ''), origin, secure == 'true',os.getenv('GEOATTEND_MAP_TILE_URL',cls.map_tile_url),os.getenv('GEOATTEND_MAP_ATTRIBUTION',cls.map_attribution))
