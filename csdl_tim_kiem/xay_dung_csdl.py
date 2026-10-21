#!/usr/bin/env python3
"""Yêu cầu 3: trích đặc trưng A/B/C cho 655 tệp và ghi vào CSDL SQLite.

Chạy từ thư mục gốc repo:  python csdl_tim_kiem/xay_dung_csdl.py
"""
import argparse
import csv
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import scipy
import soundfile as sf

from csdl import DB_MAC_DINH, ghi_csdl
from dac_trung import REPO, doc_am_thanh, ma_bam_pcm, tinh_dac_trung

DU_LIEU = REPO / 'filtered_output'


def nguon_va_nhom(r):
    """Tên nguồn và nhóm bản thu: các tệp chung nhóm có thể đến từ cùng một buổi thu."""
    url = r['collection_url']
    if 'idmt' in url:
        return 'IDMT', 'idmt:' + r['source_name'].split('_')[0]  # cùng bộ trống, vd WaveDrum02
    if 'uiowa' in url:
        return 'Iowa', 'iowa:' + r['source_original_metadata_path'].split('/')[-2]  # cùng nhạc cụ, cách đánh, độ to
    return 'Freesound', 'freesound:' + r['uploader']  # cùng người tải lên


def doc_danh_sach(du_lieu=DU_LIEU):
    """Danh sách 655 tệp theo thứ tự kiểm kê, kèm thông tin nguồn từ accepted.csv."""
    kiem_ke = list(csv.DictReader((du_lieu / 'evidence/inventory.csv').open(encoding='utf-8-sig')))
    meta = {r['output']: r for r in csv.DictReader((du_lieu / 'accepted.csv').open(encoding='utf-8-sig'))}
    thuc_te = {p.relative_to(du_lieu).as_posix() for p in (du_lieu / 'accepted').rglob('*.wav')}
    assert thuc_te == {r['relative_path'] for r in kiem_ke} == set(meta), 'Tập tệp khác hồ sơ kiểm kê'
    tep = []
    for r in kiem_ke:
        m = meta[r['relative_path']]
        nguon, nhom = nguon_va_nhom(m)
        tep.append(dict(ma_tep=int(r['index']), duong_dan=r['relative_path'], nhan=r['label'], nguon=nguon,
                        ten_goc=m['source_name'], nguoi_tai_len=m['uploader'], nhom_ban_thu=nhom,
                        thoi_luong_s=float(r['duration_s']), sha256=r['sha256']))
    return tep


def trich_xuat(tep, du_lieu=DU_LIEU):
    A, B = [], []
    for t in tep:
        p = du_lieu / t['duong_dan']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == t['sha256'], 'Âm thanh đã bị sửa: ' + t['duong_dan']
        info = sf.info(str(p))
        assert info.samplerate == 16000 and info.channels == 1
        y = doc_am_thanh(p)
        t['pcm16_sha256'] = ma_bam_pcm(y)
        a, b = tinh_dac_trung(y)
        A.append(a)
        B.append(b)
    return np.array(A), np.array(B)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db', type=Path, default=DB_MAC_DINH)
    args = ap.parse_args()
    t0 = time.perf_counter()
    tep = doc_danh_sach()
    A, B = trich_xuat(tep)
    assert np.isfinite(A).all() and np.isfinite(B).all()
    thong_tin = {'phien_ban_du_lieu': json.loads((DU_LIEU / 'summary.json').read_text())['dataset_version'],
                 'tao_luc': datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(timespec='seconds'),
                 'so_tep': len(tep), 'so_lop': len({t['nhan'] for t in tep}),
                 'so_chieu': json.dumps({'A': 21, 'B': 39, 'C': 60}),
                 'thu_vien': json.dumps({'numpy': np.__version__, 'scipy': scipy.__version__,
                                         'soundfile': sf.__version__})}
    ghi_csdl(args.db, tep, A, B, thong_tin)
    print(f'Đã ghi {len(tep)} tệp, {thong_tin["so_lop"]} lớp vào {args.db} '
          f'({args.db.stat().st_size / 1024:.0f} KB) trong {time.perf_counter() - t0:.1f} s')


if __name__ == '__main__':
    main()
