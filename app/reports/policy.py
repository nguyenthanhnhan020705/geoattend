from datetime import date, datetime, time, timedelta, timezone
import re
import unicodedata
from app.errors import ApiError

VIETNAM = timezone(timedelta(hours=7))
MAX_PDF_BYTES = 10_000_000
SUNDAY_REMINDER = 'BẠN CÒN 1 NGÀY ĐỂ NỘP BÁO CÁO NHÉ!!'
OVERDUE_REMINDER = 'TUẦN VỪA RỒI BẠN CHƯA NỘP BÁO CÁO. HÃY TRÌNH BÀY NỘI DUNG ĐÓ GỘP VỚI TUẦN NÀY NHÉ!'


def week_start_for(now: datetime) -> date:
    today = now.astimezone(VIETNAM).date()
    return today - timedelta(days=today.weekday())


def week_deadline(week_start: date) -> datetime:
    return datetime.combine(week_start + timedelta(days=7), time(), VIETNAM)


def first_required_week(created_at: datetime, enabled_at: datetime) -> date:
    return week_start_for(max(created_at, enabled_at))


def validate_week(week_start: date):
    if week_start.weekday() != 0:
        raise ApiError(422, 'INVALID_WEEK', 'Tuần báo cáo phải bắt đầu vào thứ Hai.')


def validate_pdf(filename: str, content_type: str, content: bytes) -> str:
    if len(content) > MAX_PDF_BYTES:
        raise ApiError(413, 'REPORT_TOO_LARGE', 'File PDF tối đa 10 MB.')
    name = unicodedata.normalize('NFC', filename.replace('\\', '/').rsplit('/', 1)[-1])
    name = ''.join(c for c in name if not unicodedata.category(c).startswith('C')).strip()
    if (not name.lower().endswith('.pdf') or len(name) <= 4
            or content_type.split(';', 1)[0].strip().lower() != 'application/pdf'
            or not re.match(rb'%PDF-\d\.\d(?:\s|$)', content[:12])
            or not content.rstrip().endswith(b'%%EOF')):
        raise ApiError(422, 'INVALID_PDF', 'Vui lòng chọn file PDF hợp lệ, tối đa 10 MB.')
    return name[:176] + '.pdf' if len(name) > 180 else name
