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
def test_map_configuration_and_origin(monkeypatch):
    from app.config import Settings
    monkeypatch.setenv('GEOATTEND_MAP_TILE_URL','https://tiles.example/{z}/{x}/{y}.png')
    monkeypatch.setenv('GEOATTEND_MAP_ATTRIBUTION','Example maps')
    settings=Settings.from_env()
    assert settings.map_tile_url=='https://tiles.example/{z}/{x}/{y}.png'
    assert settings.map_attribution=='Example maps'
    assert settings.map_tile_origin=='https://tiles.example'


def test_map_configuration_rejects_unsafe_urls(monkeypatch):
    import pytest
    from app.config import Settings
    for url in ('javascript:alert(1)','https://user:secret@tiles.example/{z}/{x}/{y}.png','http://tiles.example/{z}/{x}/{y}.png','https://tiles.example/no-placeholders.png'):
        monkeypatch.setenv('GEOATTEND_MAP_TILE_URL',url)
        with pytest.raises(ValueError): Settings.from_env()
def test_default_map_uses_accessible_vector_provider():
    from app.config import Settings
    settings=Settings()
    assert settings.map_kind=='vector'
    assert settings.map_style_url=='https://tiles.openfreemap.org/styles/liberty'
    assert Settings(map_tile_url='https://tiles.example/{z}/{x}/{y}.png').map_kind=='raster'
