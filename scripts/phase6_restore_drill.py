"""Local test-only PostgreSQL tooling, never loads .env or accepts remote DBs.

Run the complete drill with:
python -m pytest tests/integration/test_phase6_restore.py -q
"""
import os
import shutil
import subprocess
from pathlib import Path

from psycopg.conninfo import conninfo_to_dict


def test_connection_env(dsn):
    params=conninfo_to_dict(dsn)
    if (params.get('host') not in ('127.0.0.1','localhost','::1')
        or params.get('hostaddr',params['host']) not in ('127.0.0.1','::1','localhost')
        or not params.get('dbname','').startswith('geoattend_test_')
        or params.get('service')):
        raise ValueError('Drill requires an explicitly local geoattend_test_* database')
    # Discard inherited PG routing variables, including service/hostaddr/options.
    env={key:value for key,value in os.environ.items() if not key.startswith('PG')}
    for key,var in [('host','PGHOST'),('port','PGPORT'),('dbname','PGDATABASE'),('user','PGUSER'),('password','PGPASSWORD')]:
        if key in params:env[var]=params[key]
    env['PGCONNECT_TIMEOUT']='10'
    return env


def pg_tool(name):
    found=shutil.which(name)
    fallback=Path('C:/Program Files/PostgreSQL/17/bin')/(name+'.exe')
    if found:return found
    if fallback.is_file():return str(fallback)
    raise RuntimeError('PostgreSQL client tool unavailable: '+name)


def run_pg(name,dsn,*arguments):
    env=test_connection_env(dsn)
    result=subprocess.run([pg_tool(name),*map(str,arguments)],env=env,capture_output=True)
    if result.returncode:
        # Tool stderr may include database values. Do not propagate it into logs.
        raise RuntimeError(f'{name} failed (exit {result.returncode}); inspect only in isolated diagnostics')
