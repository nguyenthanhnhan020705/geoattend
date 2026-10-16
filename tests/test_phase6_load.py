import asyncio
import json
import logging

import pytest


def test_summary_counts_errors_and_threshold_inclusively():
    from scripts.phase6_load import summarize
    samples=[{'route':'/api/health','method':'GET','status':status,'duration_ms':ms}
             for status,ms in [(200,1),(200,20),(503,100),(200,2000),(200,2001)]]
    result=summarize(samples)
    assert result['requests']==5 and result['errors']==1
    assert result['within_2s_percent']==80
    assert result['successful_within_2s_percent']==60
    assert result['p50_ms']==100 and result['p95_ms']==2001 and result['p99_ms']==2001
    assert result['by_endpoint']['GET /api/health']['requests']==5
    with pytest.raises(ValueError):summarize([])


def test_timing_covers_final_body_and_does_not_capture_sensitive_values():
    from app.telemetry import ApiTiming
    samples=[];ticks=iter([10,10.125])
    async def endpoint(scope,receive,send):
        scope['route']=type('Route',(),{'path':'/api/admin/users/{account_id}/history'})()
        await send({'type':'http.response.start','status':200,'headers':[]})
        await send({'type':'http.response.body','body':b'GPS-secret','more_body':True})
        assert samples==[]
        await send({'type':'http.response.body','body':b'token-secret'})
    scope={'type':'http','method':'GET','path':'/api/admin/users/private-id/history',
           'query_string':b'password=secret','headers':[(b'cookie',b'token-secret')]}
    async def ignore(message):pass
    asyncio.run(ApiTiming(endpoint,samples.append,lambda:next(ticks))(scope,None,ignore))
    assert samples==[{'route':'/api/admin/users/{account_id}/history','method':'GET','status':200,'duration_ms':125.0}]
    assert 'secret' not in json.dumps(samples) and 'private-id' not in json.dumps(samples)


def test_failed_request_recorded_and_safe_formatter_hides_exception_and_message():
    from app.telemetry import ApiTiming, SafeFormatter
    samples=[]
    async def broken(scope,receive,send):raise RuntimeError('postgresql://password-secret GPS-secret')
    with pytest.raises(RuntimeError):
        asyncio.run(ApiTiming(broken,samples.append)({'type':'http','path':'/api/missing?token=secret','method':'POST'},None,None))
    assert samples[0]['route']=='UNMATCHED' and samples[0]['status']==500
    record=logging.LogRecord('uvicorn.error',logging.ERROR,'',1,'password-secret',(),(RuntimeError,RuntimeError('GPS-secret'),None))
    line=SafeFormatter().format(record)
    assert 'secret' not in line and 'ERROR' in line


def test_app_emits_sanitized_metrics_on_validation_and_database_failure(client,caplog):
    caplog.set_level(logging.INFO,logger='geoattend.api')
    response=client.post('/api/auth/login?token=TOKEN_SENTINEL',json={'username':'x','password':'PASSWORD_SENTINEL','latitude':'GPS_SENTINEL'})
    assert response.status_code==422
    client.app.state.pool.unavailable=True
    assert client.get('/api/health').status_code==503
    records=[record.api_metrics for record in caplog.records if record.name=='geoattend.api']
    assert [(row['route'],row['status']) for row in records]==[('/api/auth/login',422),('/api/health',503)]
    assert 'SENTINEL' not in json.dumps(records) and 'secret-dsn' not in json.dumps(records)
