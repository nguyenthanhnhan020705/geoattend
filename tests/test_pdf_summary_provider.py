import base64
from io import BytesIO
import json
import httpx
import pytest
from tests.pdf_fixtures import text_pdf

TEXT = 'Báo cáo mô tả công việc đã hoàn thành trong tuần cùng các kết quả kiểm thử và kế hoạch tiếp theo. ' * 4


def test_provider_sends_entire_pdf_and_returns_valid_paragraph():
    from app.reports.summary_provider import GeminiProvider, SummarySettings
    pdf = text_pdf(pages=10)
    def respond(request):
        assert request.url.host == 'generativelanguage.googleapis.com'
        assert request.headers['x-goog-api-key'] == 'test-secret'
        assert 'test-secret' not in str(request.url)
        payload = json.loads(request.content)
        inline = payload['contents'][0]['parts'][0]['inlineData']
        assert base64.b64decode(inline['data']) == pdf
        return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[
            {'text':json.dumps({'readable':True,'summary':TEXT})}]}}]})
    provider = GeminiProvider(SummarySettings(api_key='test-secret'), transport=httpx.MockTransport(respond))
    assert provider.summarize(pdf) == TEXT.strip()


@pytest.mark.parametrize('count,valid',[(79,False),(80,True),(150,True),(151,False)])
def test_word_limits(count,valid):
    from app.reports.summary_provider import validate_summary, SummaryError
    if valid:
        assert validate_summary(' '.join(['từ']*count))
    else:
        with pytest.raises(SummaryError,match='INVALID_OUTPUT'):
            validate_summary(' '.join(['từ']*count))


@pytest.mark.parametrize('value',['# Tiêu đề '+TEXT, TEXT+'\n\nĐoạn thứ hai.', '**'+TEXT+'**'])
def test_rejects_markdown_and_multiple_paragraphs(value):
    from app.reports.summary_provider import validate_summary, SummaryError
    with pytest.raises(SummaryError,match='INVALID_OUTPUT'):
        validate_summary(value)


def test_preserves_names_and_comparison_symbols_inside_plain_text():
    from app.reports.summary_provider import validate_summary
    value='Nhóm C# xử lý yêu cầu #123 với tỉ lệ lỗi <5% và thông lượng >100 lần. '+TEXT
    assert validate_summary(value)==value.strip()


def test_reads_scan_without_requiring_extractable_text():
    from PIL import Image, ImageDraw
    from app.reports.summary_provider import validate_document
    image = Image.new('RGB',(600,800),'white')
    ImageDraw.Draw(image).text((30,40),'BAO CAO TUAN: hoan thanh kiem thu',fill='black')
    stream=BytesIO(); image.save(stream,format='PDF')
    assert validate_document(stream.getvalue()) == 1


def test_rejects_broken_encrypted_and_over_limit_documents():
    from pypdf import PdfWriter
    from app.reports.summary_provider import validate_document, SummaryError
    with pytest.raises(SummaryError,match='UNREADABLE'):
        validate_document(b'%PDF-1.4\nnot a real pdf\n%%EOF')
    writer=PdfWriter();writer.add_blank_page(100,100);writer.encrypt('secret')
    stream=BytesIO();writer.write(stream)
    with pytest.raises(SummaryError,match='PDF_PASSWORD'):
        validate_document(stream.getvalue())
    with pytest.raises(SummaryError,match='PAGE_LIMIT'):
        validate_document(text_pdf(pages=1001))


@pytest.mark.parametrize('status,body,want',[
    (429,{},'RATE_LIMIT'),(403,{},'PROVIDER_AUTH'),(500,{},'PROVIDER_UNAVAILABLE'),
    (200,{'candidates':[]},'UNREADABLE'),
    (200,{'candidates':[{'finishReason':'SAFETY'}]},'UNREADABLE'),
    (200,{'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"readable":false,"summary":""}'}]}}]},'UNREADABLE'),
    (200,{'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'not json'}]}}]},'INVALID_OUTPUT')])
def test_provider_errors_are_safe(status,body,want):
    from app.reports.summary_provider import GeminiProvider, SummarySettings, SummaryError
    provider=GeminiProvider(SummarySettings(api_key='secret'),transport=httpx.MockTransport(
        lambda req:httpx.Response(status,json=body)))
    with pytest.raises(SummaryError,match=want) as exc:
        provider.summarize(text_pdf())
    assert 'secret' not in str(exc.value)


def test_timeout_and_missing_configuration():
    from app.reports.summary_provider import GeminiProvider, SummarySettings, SummaryError
    with pytest.raises(SummaryError,match='NOT_CONFIGURED'):
        GeminiProvider(SummarySettings()).summarize(text_pdf())
    def fail(req): raise httpx.ReadTimeout('secret details')
    with pytest.raises(SummaryError,match='AI_TIMEOUT'):
        GeminiProvider(SummarySettings(api_key='secret'),transport=httpx.MockTransport(fail)).summarize(text_pdf())


@pytest.mark.parametrize('value,reason',[
    (' '.join(['từ']*79),'WORD_LIMIT'),
    (TEXT+'\nĐoạn thứ hai.','PARAGRAPH_FORMAT'),
    ('**'+TEXT+'**','MARKDOWN'),
])
def test_invalid_output_reports_safe_reason_without_document_text(value,reason):
    from app.reports.summary_provider import validate_summary,SummaryError
    with pytest.raises(SummaryError) as caught:
        validate_summary(value)
    assert caught.value.code=='INVALID_OUTPUT'
    assert caught.value.reason==reason
    assert value not in str(caught.value)


def test_untrusted_error_reason_cannot_reach_worker_logs():
    from app.reports.summary_provider import SummaryError
    assert SummaryError('INVALID_OUTPUT','private provider payload').reason is None


def test_provider_keeps_complete_sentences_when_output_slightly_exceeds_limit():
    from app.reports.summary_provider import GeminiProvider,SummarySettings
    first=' '.join(['nội dung']*50)+'.'
    last=' '.join(['kế hoạch']*29)+'.'
    value=first+' '+last
    assert len(value.split())==158
    calls=[]
    def respond(request):
        calls.append(request)
        return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[
            {'text':json.dumps({'readable':True,'summary':value})}]}}]})
    result=GeminiProvider(SummarySettings(api_key='secret'),transport=httpx.MockTransport(respond)).summarize(text_pdf())
    assert result==first
    assert len(calls)==1


@pytest.mark.parametrize('value',[
    ' '.join(['từ']*158),
    ' '.join(['từ']*100)+'. '+' '.join(['từ']*81)+'.',
])
def test_never_cuts_mid_sentence_or_accepts_substantially_overlong_output(value):
    from app.reports.summary_provider import prepare_summary,SummaryError
    with pytest.raises(SummaryError,match='INVALID_OUTPUT'):
        prepare_summary(value)
