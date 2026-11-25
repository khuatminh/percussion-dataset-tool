"""Smoke tests against the real local HTTP server, including upload and playback."""
import io
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
import pytest
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope='module')
def server():
    process = subprocess.Popen([sys.executable, str(ROOT / 'csdl_tim_kiem/giao_dien.py'), '--port', '0'],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        line = process.stdout.readline()
        assert 'http://' in line, line
        yield line.split('http://')[1].split()[0]
    finally:
        process.terminate()
        process.wait(timeout=5)


def request(server, path, data=None, headers=None):
    return urlopen(Request(f'http://{server}{path}', data=data, headers=headers or {}), timeout=15)


def test_search_and_audio_range(server):
    samples = json.load(request(server, '/api/samples'))
    assert len(samples) == 655
    sample_id = samples[0]['id']
    default = json.load(request(server, f'/api/search?id={sample_id}'))
    assert default['bo'] == 'C'
    for bo in 'ABC':
        result = json.load(request(server, f'/api/search?id={sample_id}&bo={bo}'))
        assert len(result['ket_qua']) == 5
        assert sample_id not in [r['ma_tep'] for r in result['ket_qua']]
    wav = request(server, f'/audio/{sample_id}').read()
    assert wav[:4] == b'RIFF'
    partial = request(server, f'/audio/{sample_id}', headers={'Range': 'bytes=10-99'})
    assert partial.status == 206
    assert partial.read() == wav[10:100]
    with pytest.raises(HTTPError) as exc:
        request(server, f'/audio/{sample_id}', headers={'Range': 'bytes=999999999-'})
    assert exc.value.code == 416


def test_upload_preview_and_reject_bad_audio(server):
    samples = json.load(request(server, '/api/samples'))
    wav = request(server, f'/audio/{samples[0]["id"]}').read()
    result = json.load(request(server, '/api/upload?bo=C', data=wav))
    assert len(result['ket_qua']) == 5
    assert result['preview'].startswith('data:audio/wav;base64,UklGR')
    silent = io.BytesIO()
    sf.write(silent, np.zeros(16000), 16000, format='WAV')
    for invalid in [b'not audio', silent.getvalue()]:
        with pytest.raises(HTTPError) as exc:
            request(server, '/api/upload?bo=C', data=invalid)
        assert exc.value.code == 400
        assert 'error' in json.load(exc.value)


def test_request_boundaries(server):
    for path, headers, code in [('/api/search?id=1&bo=Z', {}, 400),
                                ('/api/search?id=1&bo=E', {}, 400),
                                ('/api/search?id=1&bo=D', {}, 400),
                                ('/audio/999999', {}, 400),
                                ('/../../README.md', {}, 404),
                                ('/api/samples', {'Origin': 'https://example.com'}, 403),
                                ('/api/samples', {'Host': 'example.com'}, 403)]:
        with pytest.raises(HTTPError) as exc:
            request(server, path, headers=headers)
        assert exc.value.code == code


def test_local_file_picker_fallback(server):
    sample = next((ROOT/'filtered_output/accepted/snare').glob('*.wav'))
    result=json.load(request(server,'/api/local?bo=C',data=json.dumps({'path':str(sample)}).encode()))
    assert result['filename']==sample.name
    assert len(result['ket_qua'])==5 and result['preview'].startswith('data:audio/wav;')
    with pytest.raises(HTTPError) as exc:
        request(server,'/api/local?bo=C',data=json.dumps({'path':str(ROOT/'README.md')}).encode())
    assert exc.value.code==400
    with pytest.raises(HTTPError) as exc:
        request(server,'/api/local?bo=C',data=b'[]')
    assert exc.value.code==400
