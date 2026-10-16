"""Aggregate sanitized backend samples. Load execution lives in an isolated test.

python -m pytest tests/integration/test_phase6_load.py -q
No CLI accepting application credentials or remote targets is provided.
"""
from collections import defaultdict
from math import ceil
from app.telemetry import ApiTiming


class MeasuredRequests:
    """Select at request entry, so delayed warmup completion cannot leak in."""
    def __init__(self,app,record):
        self.app=app
        self.timed=ApiTiming(app,record)

    async def __call__(self,scope,receive,send):
        measured=(scope['type']=='http' and
                  (b'x-phase6-measure',b'1') in scope.get('headers',[]))
        await (self.timed if measured else self.app)(scope,receive,send)


def summarize(samples):
    if not samples:raise ValueError('No timing samples')
    times=sorted(row['duration_ms'] for row in samples)
    def percentile(fraction):return times[max(0,ceil(len(times)*fraction)-1)]
    endpoints=defaultdict(list)
    for row in samples:endpoints[row['method']+' '+row['route']].append(row)
    return dict(requests=len(samples),errors=sum(row['status']>=400 for row in samples),
                within_2s_percent=100*sum(row['duration_ms']<=2000 for row in samples)/len(samples),
                successful_within_2s_percent=100*sum(row['duration_ms']<=2000 and row['status']<400 for row in samples)/len(samples),
                p50_ms=percentile(.50),p95_ms=percentile(.95),p99_ms=percentile(.99),max_ms=times[-1],
                by_endpoint={key:{'requests':len(rows),'errors':sum(row['status']>=400 for row in rows),
                                  'p95_ms':sorted(row['duration_ms'] for row in rows)[ceil(len(rows)*.95)-1],
                                  'max_ms':max(row['duration_ms'] for row in rows)} for key,rows in sorted(endpoints.items())})
