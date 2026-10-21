from datetime import date, datetime
import pytest
from app.errors import ApiError


@pytest.mark.parametrize('moment,want', [
    ('2026-10-25T16:59:59+00:00', date(2026, 10, 19)),
    ('2026-10-25T17:00:00+00:00', date(2026, 10, 26)),
    ('2027-01-01T00:00:00+00:00', date(2026, 12, 28)),
])
def test_vietnam_week_and_deadline(moment, want):
    from app.reports.policy import week_start_for, week_deadline
    assert week_start_for(datetime.fromisoformat(moment)) == want
    assert week_deadline(date(2026, 10, 19)).isoformat() == '2026-10-26T00:00:00+07:00'


def test_first_required_week_uses_later_activation():
    from app.reports.policy import first_required_week
    assert first_required_week(datetime.fromisoformat('2026-10-01T00:00:00+00:00'),
                               datetime.fromisoformat('2026-10-20T00:00:00+00:00')) == date(2026, 10, 19)
    assert first_required_week(datetime.fromisoformat('2026-10-27T00:00:00+00:00'),
                               datetime.fromisoformat('2026-10-20T00:00:00+00:00')) == date(2026, 10, 26)


def test_pdf_limit_and_unicode_filename():
    from app.reports.policy import validate_pdf
    pdf = b'%PDF-1.4\n' + b' ' * (10_000_000 - 15) + b'%%EOF\n'
    assert len(pdf) == 10_000_000
    assert validate_pdf('../Báo cáo.pdf', 'application/pdf', pdf) == 'Báo cáo.pdf'
    with pytest.raises(ApiError) as error:
        validate_pdf('report.pdf', 'application/pdf', pdf + b' ')
    assert error.value.code == 'REPORT_TOO_LARGE'


@pytest.mark.parametrize('name,mime,pdf', [
    ('a.pdf','application/pdf',b''), ('a.txt','application/pdf',b'%PDF-1.4\n%%EOF'),
    ('a.pdf','text/html',b'%PDF-1.4\n%%EOF'), ('a.pdf','application/pdf',b'<html>%%EOF'),
    ('a.pdf','application/pdf',b'%PDF-1.4\nincomplete'),
])
def test_invalid_pdf_rejected(name,mime,pdf):
    from app.reports.policy import validate_pdf
    with pytest.raises(ApiError):
        validate_pdf(name,mime,pdf)
