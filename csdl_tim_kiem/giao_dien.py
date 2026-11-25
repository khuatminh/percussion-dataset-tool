#!/usr/bin/env python3
"""Yêu cầu 5: giao diện demo chạy cục bộ. Chạy: python csdl_tim_kiem/giao_dien.py rồi mở http://127.0.0.1:8765."""
import argparse
import base64
import io
import json
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote

import soundfile as sf
import numpy as np

from csdl import CSDL
from dac_trung import LoiAmThanh, REPO

MAX_BYTES = 30 * 1024 * 1024
MAX_SECONDS = 120
WEB = Path(__file__).with_name('web')


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, data, content_type, status=200):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def json(self, value, status=200):
        self.send_bytes(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(),
                        'application/json; charset=utf-8', status)

    def valid_host(self):
        # Chỉ phục vụ trang cục bộ; không cho một trang bên ngoài gửi yêu cầu upload.
        host = self.headers.get('Host', '')
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        origin = self.headers.get('Origin')
        return host in allowed and (not origin or origin in {'http://' + h for h in allowed})

    def sample(self, sample_id):
        try:
            row = self.server.db.tep[int(sample_id)]
        except (ValueError, KeyError):
            raise ValueError('Không tìm thấy tệp trong kho.') from None
        return row, REPO / 'filtered_output' / row['duong_dan']

    def search(self, path, bo):
        if bo not in ('A', 'B', 'C'):
            raise ValueError('Bộ đặc trưng phải là A, B hoặc C.')
        result = self.server.db.tim_kiem(path, bo)  # tìm bằng PostgreSQL + pgvector
        return {k: v for k, v in result.items() if k not in {'u', 'a', 'b'}}

    def do_GET(self):
        if not self.valid_host():
            return self.json({'error': 'Chỉ cho phép truy cập cục bộ.'}, 403)
        url = urlparse(self.path)
        params = parse_qs(url.query)
        try:
            if url.path in ('/', '/app.js', '/style.css'):
                name, kind = {'/': ('index.html', 'text/html; charset=utf-8'),
                              '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                              '/style.css': ('style.css', 'text/css; charset=utf-8')}[url.path]
                return self.send_bytes((WEB / name).read_bytes(), kind)
            if url.path == '/api/samples':
                return self.json([{'id': t['ma_tep'], 'label': t['nhan'],
                                   'name': Path(t['duong_dan']).name, 'duration': t['thoi_luong_s']}
                                  for t in self.server.db.tep.values()])
            if url.path == '/api/search':
                _, path = self.sample(params.get('id', [''])[0])
                return self.json(self.search(path, params.get('bo', ['C'])[0]))
            if url.path.startswith('/audio/'):
                _, path = self.sample(url.path.removeprefix('/audio/'))
                data = path.read_bytes()
                # Range requests let native browser players seek and replay clips.
                requested = self.headers.get('Range')
                if requested:
                    try:
                        unit, interval = requested.split('=', 1)
                        start, end = interval.split('-', 1)
                        if unit != 'bytes':
                            raise ValueError
                        left = int(start) if start else max(0, len(data) - int(end))
                        right = min(int(end), len(data) - 1) if start and end else len(data) - 1
                        if not 0 <= left <= right < len(data):
                            raise ValueError
                    except ValueError:
                        self.send_response(416)
                        self.send_header('Content-Range', f'bytes */{len(data)}')
                        self.send_header('Content-Length', '0')
                        self.end_headers()
                        return
                    self.send_response(206)
                    self.send_header('Content-Type', 'audio/wav')
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Content-Range', f'bytes {left}-{right}/{len(data)}')
                    self.send_header('Content-Length', str(right - left + 1))
                    self.end_headers()
                    self.wfile.write(data[left:right + 1])
                    return
                return self.send_bytes(data, 'audio/wav')
            self.json({'error': 'Không tìm thấy trang.'}, 404)
        except (ValueError, OSError, ImportError) as exc:
            self.json({'error': str(exc)}, 400)

    def do_POST(self):
        if not self.valid_host():
            return self.json({'error': 'Chỉ cho phép truy cập cục bộ.'}, 403)
        url = urlparse(self.path)
        if url.path not in ('/api/upload', '/api/local'):
            return self.json({'error': 'Không tìm thấy trang.'}, 404)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_BYTES:
                return self.json({'error': 'Chọn tệp có dung lượng từ 1 byte đến 30 MB.'}, 413)
            data = self.rfile.read(size)
            original_name = None
            if url.path == '/api/local':
                payload = json.loads(data)
                if not isinstance(payload, dict):
                    raise ValueError('Yêu cầu phải chứa đường dẫn file âm thanh.')
                name = str(payload.get('path', '')).strip().strip('"').strip("'")
                if name.startswith('file://'):
                    name = unquote(urlparse(name).path)
                source = Path(name).expanduser()
                if not source.is_absolute() or not source.is_file():
                    raise ValueError('Dán đường dẫn đầy đủ tới một file âm thanh có trên máy.')
                if source.suffix.lower() not in {'.wav','.wave','.mp3','.flac','.ogg','.aif','.aiff','.au','.opus'}:
                    raise ValueError('Chỉ nhận đường dẫn tới file âm thanh WAV, MP3, FLAC, OGG, AIFF, AU hoặc OPUS.')
                if not 0 < source.stat().st_size <= MAX_BYTES:
                    raise ValueError('File phải có dung lượng từ 1 byte đến 30 MB.')
                original_name = source.name
                data = source.read_bytes()
            with tempfile.TemporaryDirectory(prefix='percussion-query-') as folder:
                path = Path(folder) / 'query.audio'
                path.write_bytes(data)
                try:
                    info = sf.info(str(path))
                except Exception:
                    raise LoiAmThanh('Không đọc được âm thanh. Hãy thử WAV, MP3, FLAC, OGG hoặc AIFF.') from None
                if info.duration > MAX_SECONDS:
                    raise LoiAmThanh('Chọn đoạn âm thanh dài tối đa 120 giây.')
                if info.channels > 8:
                    raise LoiAmThanh('Chọn tệp có tối đa 8 kênh âm thanh.')
                bo = parse_qs(url.query).get('bo', ['C'])[0]
                result = self.search(path, bo)
                # WAV preview supports formats browsers cannot play directly (e.g. AIFF).
                y, sr = sf.read(str(path), dtype='float32', always_2d=True)
                preview = io.BytesIO()
                mono = y.mean(axis=1)
                power = np.mean(y.astype(np.float64)**2, axis=0)
                if np.mean(mono.astype(np.float64)**2) < .1 * power.max():
                    mono = y[:, int(power.argmax())]
                sf.write(preview, mono, sr, format='WAV', subtype='PCM_16')
                result['preview'] = 'data:audio/wav;base64,' + base64.b64encode(preview.getvalue()).decode()
                if original_name:
                    result['filename'] = original_name
                self.json(result)
        except (ValueError, OSError, ImportError) as exc:
            self.json({'error': str(exc)}, 400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    # Một luồng xử lý: dùng chung một kết nối PostgreSQL cho mọi yêu cầu.
    server = HTTPServer(('127.0.0.1', args.port), Handler)
    server.db = CSDL()
    print(f'Mở giao diện: http://127.0.0.1:{server.server_port}  (Ctrl+C để dừng)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.db.con.close()
        server.server_close()


if __name__ == '__main__':
    main()
