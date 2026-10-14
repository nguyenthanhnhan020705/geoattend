import os
from urllib.parse import urlsplit
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = ''
    migration_database_url: str = ''
    origin: str = 'http://127.0.0.1:8000'
    secure_cookies: bool = False

    def __post_init__(self):
        parsed = urlsplit(self.origin)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('GEOATTEND_ORIGIN phải là scheme/host/port.')
        if parsed.scheme == 'https' and not self.secure_cookies:
            raise ValueError('HTTPS yêu cầu cookie Secure.')


    @classmethod
    def from_env(cls):
        origin = os.getenv('GEOATTEND_ORIGIN', 'http://127.0.0.1:8000')
        secure = os.getenv('GEOATTEND_SECURE_COOKIES', str(origin.startswith('https://'))).lower()
        if secure not in ('true', 'false'):
            raise ValueError('GEOATTEND_SECURE_COOKIES phải là true hoặc false.')
        return cls(os.getenv('GEOATTEND_DATABASE_URL', ''), os.getenv('GEOATTEND_MIGRATION_DATABASE_URL', ''), origin, secure == 'true')
