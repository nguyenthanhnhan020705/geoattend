import pytest


def test_https_requires_secure_cookie(monkeypatch):
    from app.config import Settings
    monkeypatch.setenv('GEOATTEND_ORIGIN', 'https://example.com')
    monkeypatch.setenv('GEOATTEND_SECURE_COOKIES', 'false')
    with pytest.raises(ValueError):
        Settings.from_env()


def test_origin_has_no_path():
    from app.config import Settings
    with pytest.raises(ValueError):
        Settings(origin='https://example.com/path', secure_cookies=True)
