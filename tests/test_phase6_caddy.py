"""Opt-in real proxy failure probe; never binds public ports or calls app DBs."""
import json
import os
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest


def test_proxy_upstream_failure_logs_do_not_capture_request_secrets(tmp_path):
    binary=os.getenv('GEOATTEND_CADDY_BINARY')
    if not binary:pytest.skip('Set GEOATTEND_CADDY_BINARY for the real local proxy privacy probe')
    binary=str(Path(binary).resolve())
    assert Path(binary).is_file()
    # Reserve the upstream socket without listening, so it cannot accidentally
    # contact a running application, and select a separate loopback proxy port.
    with socket.socket() as upstream,socket.socket() as listener:
        upstream.bind(('127.0.0.1',0));listener.bind(('127.0.0.1',0))
        port=listener.getsockname()[1]
        origin=f'http://127.0.0.1:{port}'
        env=os.environ.copy()
        env.update(GEOATTEND_HOST=origin,APPDATA=str(tmp_path),XDG_CONFIG_HOME=str(tmp_path),XDG_DATA_HOME=str(tmp_path))
        adapted=subprocess.run([binary,'adapt','--config','deploy/Caddyfile.example','--adapter','caddyfile'],env=env,capture_output=True,text=True)
        assert adapted.returncode==0
        config=json.loads(adapted.stdout);config['admin']={'disabled':True}
        for server in config['apps']['http']['servers'].values():server['listen']=[f'127.0.0.1:{port}']
        def isolate(node):
            if isinstance(node,dict):
                if node.get('handler')=='reverse_proxy':node['upstreams']=[{'dial':f'127.0.0.1:{upstream.getsockname()[1]}'}]
                for value in node.values():isolate(value)
            elif isinstance(node,list):
                for value in node:isolate(value)
        isolate(config)
        path=tmp_path/'caddy.json';path.write_text(json.dumps(config),encoding='utf-8')
        log_path=tmp_path/'proxy.log'
        listener.close()
        with log_path.open('w',encoding='utf-8') as output:
            process=subprocess.Popen([binary,'run','--config',str(path)],env=env,stdout=output,stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:
                with httpx.Client(base_url=origin,timeout=2,trust_env=False) as client:
                    for _ in range(100):
                        assert process.poll() is None
                        try:
                            if client.get('/probe').status_code==502:break
                        except httpx.TransportError:pass
                        time.sleep(.05)
                    else:pytest.fail('Loopback Caddy did not become ready')
                    response=client.get('/probe?token=TOKEN_SENTINEL&latitude=GPS_SENTINEL',headers={'X-Probe':'PASSWORD_SENTINEL','Cookie':'probe=COOKIE_SENTINEL'})
                    assert response.status_code==502
            finally:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        assert 'SENTINEL' not in log_path.read_text(encoding='utf-8')
