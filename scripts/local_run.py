"""Local-only launcher. Reads ignored .env without displaying connection secrets."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from psycopg.conninfo import make_conninfo
from scripts.console import configure_console

ROOT = Path(__file__).resolve().parents[1]


def local_environment(path, mode, inherited=None):
    values = {}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if '=' not in line:
            raise ValueError('Dòng cấu hình .env không hợp lệ.')
        key,value = line.split('=',1)
        value = value.strip()
        if len(value)>=2 and value[0]==value[-1] and value[0] in ('"',"'"):
            value = value[1:-1]
        values[key.strip()] = value
    administrator = mode in ('bootstrap-admin','migrate')
    target = 'GEOATTEND_MIGRATION_DATABASE_URL' if administrator else 'GEOATTEND_DATABASE_URL'
    dsn = values.get(target)
    if not dsn:
        names = {'host':'SUPABASE_DB_HOST','port':'SUPABASE_DB_PORT','dbname':'SUPABASE_DB_NAME',
                 'user':'SUPABASE_DB_USER' if administrator else 'GEOATTEND_RUNTIME_DB_USER',
                 'password':'SUPABASE_DB_PASSWORD' if administrator else 'GEOATTEND_RUNTIME_DB_PASSWORD'}
        missing = [name for name in names.values() if not values.get(name)]
        if missing:
            raise ValueError('Thiếu cấu hình: '+', '.join(missing))
        dsn = make_conninfo(**{key:values[name] for key,name in names.items()},sslmode=values.get('SUPABASE_DB_SSLMODE','require'))
    env = {k:v for k,v in (inherited if inherited is not None else os.environ).items() if not k.startswith(('GEOATTEND_','SUPABASE_DB_'))}
    env[target] = dsn
    env['GEOATTEND_ORIGIN'] = values.get('GEOATTEND_ORIGIN','http://127.0.0.1:8000')
    env['GEOATTEND_SECURE_COOKIES'] = values.get('GEOATTEND_SECURE_COOKIES','false')
    for key in ('GEOATTEND_FRONTEND_ORIGIN','GEOATTEND_MAP_TILE_URL','GEOATTEND_MAP_ATTRIBUTION','GEOATTEND_MAP_BACKGROUND','GEOATTEND_MAP_STYLE_URL'):
        if key in values:
            env[key]=values[key]
    if mode=='migrate':
        # Only migration receives both credentials to grant runtime access.
        env['GEOATTEND_DATABASE_URL'] = local_environment(path,'serve',{})['GEOATTEND_DATABASE_URL']
    return env


def main():
    configure_console()
    parser = argparse.ArgumentParser(description='Chạy GeoAttend từ .env local')
    parser.add_argument('mode',choices=('serve','bootstrap-admin','maintenance','migrate'))
    parser.add_argument('--once',action='store_true',help='Maintenance một lần')
    args = parser.parse_args()
    try:
        env = local_environment(ROOT/'.env',args.mode)
    except (OSError,ValueError):
        raise SystemExit('Không thể nạp cấu hình local; kiểm tra .env và các khóa kết nối, không gửi mật khẩu vào chat.')
    if args.mode == 'serve':
        command = ['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000']
    else:
        module = {'bootstrap-admin':'bootstrap_admin','maintenance':'maintenance','migrate':'migrate'}[args.mode]
        command = ['-m','scripts.'+module]
        if args.mode=='maintenance' and args.once:
            command.append('--once')
    try:
        raise SystemExit(subprocess.call([sys.executable,*command],cwd=ROOT,env=env))
    except KeyboardInterrupt:
        return


if __name__=='__main__':
    main()
