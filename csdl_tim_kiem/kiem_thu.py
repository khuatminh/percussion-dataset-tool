#!/usr/bin/env python3
"""Kiểm thử nhanh cho CSDL và tìm kiếm. Chạy từ thư mục gốc repo:  python -m pytest csdl_tim_kiem/kiem_thu.py"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cay_kd import CayKD, tim_tuan_tu  # noqa: E402
from csdl import CSDL  # noqa: E402
from dac_trung import REPO, LoiAmThanh  # noqa: E402


@pytest.fixture(scope='module')
def db():
    return CSDL()


@pytest.fixture
def tmp():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def test_cay_kd_giong_vet_can():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 21))
    X[50] = X[51]  # hai điểm trùng nhau để thử trường hợp bằng khoảng cách
    cay = CayKD(X)
    for q in rng.normal(size=(100, 21)):
        assert cay.tim(q, 5, [3]) == pytest.approx(tim_tuan_tu(X, np.arange(400), q, 5, [3]))


def test_csdl_day_du(db):
    assert len(db.ma) == 655 and len({t['nhan'] for t in db.tep.values()}) == 13
    assert {bo: db.U[bo].shape[1] for bo in 'ABC'} == {'A': 21, 'B': 39, 'C': 60}
    # Mục 10.2: d_C² = ½d_A² + ½d_B² với từng cặp tệp
    d2 = {bo: np.sum((db.U[bo][0] - db.U[bo][1:]) ** 2, axis=1) for bo in 'ABC'}
    assert np.allclose(d2['C'], (d2['A'] + d2['B']) / 2)


def test_truy_van_trung_tep_trong_kho_bi_bo(db):
    t = db.tep[db.ma[10]]
    kq = db.tim_kiem(REPO / 'filtered_output' / t['duong_dan'])
    assert kq['trung_tep_trong_kho'] == [t['ma_tep']]
    assert len(kq['ket_qua']) == 5 and t['ma_tep'] not in [r['ma_tep'] for r in kq['ket_qua']]
    d = [r['khoang_cach'] for r in kq['ket_qua']]
    assert d == sorted(d)


def test_stereo_44k1_tim_lai_ban_goc(db, tmp):
    t = db.tep[db.ma[200]]
    y, _ = sf.read(str(REPO / 'filtered_output' / t['duong_dan']))
    z = resample_poly(y, 441, 160)
    sf.write(str(tmp / 'q.wav'), np.c_[z, z] * 0.5, 44100, subtype='PCM_16')
    kq = db.tim_kiem(tmp / 'q.wav')
    assert kq['trung_tep_trong_kho'] == [] and kq['ket_qua'][0]['ma_tep'] == t['ma_tep']


def test_tu_choi_tep_im_lang_va_qua_ngan(db, tmp):
    sf.write(str(tmp / 'im.wav'), np.zeros(16000), 16000)
    with pytest.raises(LoiAmThanh):
        db.tim_kiem(tmp / 'im.wav')
    sf.write(str(tmp / 'ngan.wav'), np.random.default_rng(1).normal(size=800) * 0.3, 16000)
    with pytest.raises(LoiAmThanh):
        db.tim_kiem(tmp / 'ngan.wav')
    (tmp / 'hong.wav').write_bytes(b'khong phai am thanh')
    with pytest.raises(LoiAmThanh):
        db.tim_kiem(tmp / 'hong.wav')


def test_nhac_cu_ngoai_13_lop_van_tra_ve_5_ket_qua(db, tmp):
    t = np.arange(16000) / 16000
    chuong = sum(np.sin(2 * np.pi * f * t) for f in [880, 2390, 4100]) * np.exp(-4 * t)
    sf.write(str(tmp / 'chuong.wav'), chuong / 4, 16000)
    assert len(db.tim_kiem(tmp / 'chuong.wav', 'A')['ket_qua']) == 5
