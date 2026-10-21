"""Exercise the deployment formatter in a fresh interpreter (no global side effects)."""
import json
import subprocess
import sys


def test_deployment_logging_hides_third_party_messages_and_exception_values():
    program="""
import json,logging,logging.config
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
logging.config.dictConfig(json.load(open('deploy/logging.json')))
try:
    raise RuntimeError('GPS_SENTINEL postgresql://PASSWORD_SENTINEL TOKEN_SENTINEL')
except RuntimeError:
    logging.getLogger('uvicorn.error').exception('PASSWORD_SENTINEL')
logging.getLogger('psycopg.pool').warning('TOKEN_SENTINEL')
with TestClient(create_app(Settings())) as client:
    assert client.get('/api/health?token=TOKEN_SENTINEL').status_code == 503
    assert client.post('/api/auth/login',json={'username':'x','password':'PASSWORD_SENTINEL','longitude':'GPS_SENTINEL'}).status_code == 422
"""
    result=subprocess.run([sys.executable,'-c',program],capture_output=True,text=True)
    assert result.returncode==0
    assert 'SENTINEL' not in result.stdout+result.stderr
    records=[json.loads(line) for line in result.stdout.splitlines()]
    metrics=[record for record in records if record['event']=='api_request']
    assert [(record['route'],record['status']) for record in metrics]==[('/api/health',503),('/api/auth/login',422)]
    assert any(record['logger']=='uvicorn.error' and record['level']=='ERROR' for record in records)
    assert all('timestamp' in record for record in records)
