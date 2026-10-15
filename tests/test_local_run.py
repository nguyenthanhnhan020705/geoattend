from psycopg.conninfo import conninfo_to_dict
import pytest


def test_local_runtime_and_admin_roles_separated(tmp_path):
    from scripts.local_run import local_environment
    password="space's \\ password"
    envfile=tmp_path/'.env'
    envfile.write_text("SUPABASE_DB_HOST=pooler.example\nSUPABASE_DB_PORT=5432\nSUPABASE_DB_NAME=postgres\nSUPABASE_DB_USER=postgres.ref\nSUPABASE_DB_PASSWORD=Admin-secret\nGEOATTEND_RUNTIME_DB_USER=runtime.ref\nGEOATTEND_RUNTIME_DB_PASSWORD="+password+'\n',encoding='utf-8')
    serve=local_environment(envfile,'serve',{})
    assert conninfo_to_dict(serve['GEOATTEND_DATABASE_URL'])['password']==password
    assert conninfo_to_dict(serve['GEOATTEND_DATABASE_URL'])['user']=='runtime.ref'
    assert 'GEOATTEND_MIGRATION_DATABASE_URL' not in serve
    admin=local_environment(envfile,'bootstrap-admin',{})
    assert conninfo_to_dict(admin['GEOATTEND_MIGRATION_DATABASE_URL'])['user']=='postgres.ref'
    assert 'GEOATTEND_DATABASE_URL' not in admin
    assert local_environment(envfile,'maintenance',{})==serve


def test_local_missing_key_does_not_expose_password(tmp_path):
    from scripts.local_run import local_environment
    envfile=tmp_path/'.env'; envfile.write_text('SUPABASE_DB_PASSWORD=DoNotPrintSecret\n',encoding='utf-8')
    with pytest.raises(ValueError) as error:
        local_environment(envfile,'serve',{})
    assert 'DoNotPrintSecret' not in str(error.value)


def test_direct_dsn_and_quoted_values_supported(tmp_path):
    from scripts.local_run import local_environment
    envfile=tmp_path/'.env'
    envfile.write_text('GEOATTEND_DATABASE_URL="host=127.0.0.1 dbname=app user=worker password=secret"\nGEOATTEND_ORIGIN="http://127.0.0.1:8000"\n',encoding='utf-8')
    result=local_environment(envfile,'serve',{})
    assert conninfo_to_dict(result['GEOATTEND_DATABASE_URL'])['user']=='worker'
    assert result['GEOATTEND_ORIGIN']=='http://127.0.0.1:8000'


def test_serve_does_not_inherit_admin_secret(tmp_path):
    from scripts.local_run import local_environment
    envfile=tmp_path/'.env'; envfile.write_text('GEOATTEND_DATABASE_URL=host=localhost user=worker\n',encoding='utf-8')
    result=local_environment(envfile,'serve',{'GEOATTEND_MIGRATION_DATABASE_URL':'postgresql://admin:secret@localhost/postgres','SUPABASE_DB_PASSWORD':'secret'})
    assert 'GEOATTEND_MIGRATION_DATABASE_URL' not in result
    assert 'SUPABASE_DB_PASSWORD' not in result


def test_migration_environment_contains_runtime_for_grants(tmp_path):
    from scripts.local_run import local_environment
    envfile=tmp_path/'.env'
    envfile.write_text('GEOATTEND_MIGRATION_DATABASE_URL=host=localhost user=postgres\nGEOATTEND_DATABASE_URL=host=localhost user=worker\n',encoding='utf-8')
    result=local_environment(envfile,'migrate',{})
    assert conninfo_to_dict(result['GEOATTEND_DATABASE_URL'])['user']=='worker'
    assert conninfo_to_dict(result['GEOATTEND_MIGRATION_DATABASE_URL'])['user']=='postgres'


def test_launcher_preserves_public_map_config(tmp_path):
    from scripts.local_run import local_environment
    path=tmp_path/'.env'
    path.write_text('GEOATTEND_DATABASE_URL=host=localhost user=worker\nGEOATTEND_MAP_TILE_URL=https://tiles.example/{z}/{x}/{y}.png\nGEOATTEND_MAP_ATTRIBUTION=Example\n',encoding='utf-8')
    env=local_environment(path,'serve',{})
    assert env['GEOATTEND_MAP_TILE_URL']=='https://tiles.example/{z}/{x}/{y}.png'
    assert env['GEOATTEND_MAP_ATTRIBUTION']=='Example'
    path.write_text(path.read_text(encoding='utf-8')+'GEOATTEND_MAP_BACKGROUND=vector\nGEOATTEND_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty\n',encoding='utf-8')
    env=local_environment(path,'serve',{})
    assert env['GEOATTEND_MAP_BACKGROUND']=='vector'
    assert env['GEOATTEND_MAP_STYLE_URL']=='https://tiles.openfreemap.org/styles/liberty'
