import pytest


@pytest.mark.parametrize('dsn',[
    'postgresql://postgres@db.example.com/geoattend_test_fake',
    'postgresql://postgres@127.0.0.1/geoattend',
    'host=127.0.0.1,db.example.com dbname=geoattend_test_fake',
    'hostaddr=192.0.2.1 host=127.0.0.1 dbname=geoattend_test_fake',
])
def test_drill_refuses_nonlocal_or_application_database(dsn):
    from scripts.phase6_restore_drill import test_connection_env
    with pytest.raises(ValueError):test_connection_env(dsn)


def test_drill_connection_uses_environment_not_command_arguments():
    from scripts.phase6_restore_drill import test_connection_env
    env=test_connection_env('host=127.0.0.1 port=55440 dbname=geoattend_test_fixture user=tester password=SECRET')
    assert env['PGPASSWORD']=='SECRET' and env['PGDATABASE']=='geoattend_test_fixture'
    assert env['PGHOST']=='127.0.0.1' and env['PGPORT']=='55440'
