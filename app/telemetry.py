"""Request timing without bodies, query strings, IDs, cookies or exception text."""
import json
import logging
from datetime import datetime,timezone
from time import perf_counter

logger=logging.getLogger('geoattend.api')


def log_sample(sample):
    logger.info('api_request',extra={'api_metrics':sample})


class SafeFormatter(logging.Formatter):
    """Production formatter: never interpolate third-party messages/tracebacks.

    Full diagnostics can contain SQL row values or DSNs. Inspect them only in
    an isolated reproduction; public runtime logs expose level/category only.
    """
    def format(self,record):
        data={'timestamp':datetime.fromtimestamp(record.created,timezone.utc).isoformat(),
              'level':record.levelname,'logger':record.name,'event':'diagnostic'}
        if record.name=='geoattend.api' and hasattr(record,'api_metrics'):
            data.update(event='api_request',**record.api_metrics)
        return json.dumps(data,ensure_ascii=True)


class ApiTiming:
    def __init__(self,app,record=log_sample,timer=perf_counter):
        self.app,self.record,self.timer=app,record,timer

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or not scope['path'].startswith('/api/'):
            return await self.app(scope,receive,send)
        start=self.timer();status=500;completed=False
        def finish():
            nonlocal completed
            if completed:return
            completed=True
            route=getattr(scope.get('route'),'path','UNMATCHED')
            method=scope['method'] if scope['method'] in ('GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS') else 'OTHER'
            self.record(dict(route=route,method=method,status=status,
                             duration_ms=round((self.timer()-start)*1000,3)))
        async def timed_send(message):
            nonlocal status
            if message['type']=='http.response.start':status=message['status']
            await send(message)
            if message['type']=='http.response.body' and not message.get('more_body',False):finish()
        try:
            await self.app(scope,receive,timed_send)
        finally:
            # Includes exceptions/disconnects; a partial 200 is a failed request.
            if not completed:
                status=500
                finish()
