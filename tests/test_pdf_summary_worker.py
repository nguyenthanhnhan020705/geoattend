import subprocess
import pytest


def test_local_worker_receives_secret_but_web_does_not(tmp_path):
    from scripts.local_run import local_environment
    path=tmp_path/'.env'
    path.write_text('GEOATTEND_DATABASE_URL=host=localhost user=worker\nGEOATTEND_GEMINI_API_KEY=private-key\nGEOATTEND_SUMMARY_MODEL=gemini-3.8-flash\n',encoding='utf-8')
    assert local_environment(path,'pdf-summary',{})['GEOATTEND_GEMINI_API_KEY']=='private-key'
    assert 'GEOATTEND_GEMINI_API_KEY' not in local_environment(path,'serve',{})


def test_provider_subprocess_has_hard_deadline(monkeypatch):
    from scripts.pdf_summary_worker import BoundedGeminiProvider
    from app.reports.summary_provider import SummarySettings,SummaryError
    def timeout(*args,**kwargs): raise subprocess.TimeoutExpired('worker',60)
    monkeypatch.setattr(subprocess,'run',timeout)
    with pytest.raises(SummaryError,match='AI_TIMEOUT'):
        BoundedGeminiProvider(SummarySettings()).summarize(b'pdf')
