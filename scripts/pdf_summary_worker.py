"""Independent PDF worker; never run inside the web or attendance maintenance."""
import argparse
import json
import subprocess
import sys
import time
import psycopg
from psycopg.rows import dict_row
from app.config import Settings
from app.reports import summaries
from app.reports.summary_provider import GeminiProvider, SummarySettings, SummaryError, PROMPT_VERSION
from scripts.console import configure_console


class BoundedGeminiProvider:
    """A subprocess bounds parsing, memory lifetime and network time per document."""
    def __init__(self, settings):
        self.model=settings.model

    def summarize(self,pdf):
        try:
            result=subprocess.run([sys.executable,'-m','scripts.pdf_summary_worker','--provider-once'],
                                  input=bytes(pdf),capture_output=True,timeout=60)
        except subprocess.TimeoutExpired:
            raise SummaryError('AI_TIMEOUT') from None
        if result.returncode:
            raise SummaryError('PROVIDER_UNAVAILABLE')
        try:
            output=json.loads(result.stdout)
        except (ValueError,UnicodeError):
            raise SummaryError('INVALID_OUTPUT') from None
        if output.get('error'):
            raise SummaryError(output['error'],output.get('reason'))
        return output['summary']


def process_one(dsn,provider,*,limit=20):
    with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=10) as conn:
        if not summaries.ready(conn):
            raise SummaryError('SUMMARY_UNAVAILABLE')
        summaries.discover(conn,limit)
        job=summaries.claim(conn)
    if job is None:
        return False
    # No DB connection or transaction is alive during the external API call.
    try:
        text=provider.summarize(bytes(job['pdf']))
        code=None
    except SummaryError as error:
        text=None;code=error.code
        if error.reason:
            print(json.dumps({'event':'pdf_summary_rejected','reason':error.reason}),flush=True)
    except Exception:
        # Never log provider exception text: it can contain private payloads.
        text=None;code='PROVIDER_UNAVAILABLE'
    with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=10) as conn:
        summaries.finish(conn,job,summary=text,error_code=code,
                         model=provider.model,prompt_version=PROMPT_VERSION)
    return True


def main():
    configure_console()
    parser=argparse.ArgumentParser(description='Worker tóm tắt PDF độc lập')
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--backfill',action='store_true',help='Xử lý tối đa --limit file rồi dừng')
    parser.add_argument('--dry-run',action='store_true',help='Chỉ đếm, không ghi DB hoặc gọi AI')
    parser.add_argument('--limit',type=int,default=20)
    parser.add_argument('--provider-once',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if not 1<=args.limit<=1000:
        raise SystemExit('--limit phải từ 1 đến 1000.')
    settings=SummarySettings.from_env()
    if args.provider_once:
        try:
            summary=GeminiProvider(settings).summarize(sys.stdin.buffer.read(10_000_001))
            output={'summary':summary}
        except SummaryError as error:
            output={'error':error.code,'reason':error.reason}
        sys.stdout.buffer.write(json.dumps(output,ensure_ascii=True).encode('ascii'))
        return
    dsn=Settings.from_env().database_url
    if not dsn:
        raise SystemExit('Thiếu GEOATTEND_DATABASE_URL.')
    if not settings.api_key and not args.dry_run:
        raise SystemExit('Thiếu GEOATTEND_GEMINI_API_KEY; chưa nhận job hoặc gọi AI.')
    provider=BoundedGeminiProvider(settings)
    processed=0
    try:
        if args.dry_run:
            with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=10) as conn:
                conn.execute('SET TRANSACTION READ ONLY')
                if not summaries.ready(conn):
                    raise SummaryError('SUMMARY_UNAVAILABLE')
                count=conn.execute('''SELECT count(*) AS n FROM geoattend.weekly_reports r WHERE NOT EXISTS
                    (SELECT 1 FROM geoattend.pdf_summaries s WHERE s.report_id=r.id AND s.content_sha256=r.content_sha256)''').fetchone()['n']
            print(f'PDF chưa có job: {count}. Không ghi dữ liệu hoặc gọi AI.')
            return
        while True:
            try:
                worked=process_one(dsn,provider,limit=args.limit)
                processed+=int(worked)
                if worked:
                    print(f'Đã xử lý {processed} job; kết quả được lưu trong database.',flush=True)
                if args.once or (args.backfill and (processed>=args.limit or not worked)):
                    return
                if not worked:
                    time.sleep(3)
            except (psycopg.Error,SummaryError):
                print('Worker chưa xử lý được; kiểm tra cấu hình, migration, quyền và database.',flush=True)
                if args.once or args.backfill:
                    raise SystemExit(1)
                time.sleep(5)
    except KeyboardInterrupt:
        print('Đã dừng worker tóm tắt PDF.')


if __name__=='__main__':
    main()
