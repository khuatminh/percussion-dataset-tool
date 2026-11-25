#!/usr/bin/env python3
"""Kiểm thử nhanh cho CSDL và tìm kiếm. Chạy từ thư mục gốc repo:  python -m pytest csdl_tim_kiem/kiem_thu.py"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import psycopg
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


def test_vector_trong_postgres_khop_gia_tri_goc(db):
    hang = db.con.execute('SELECT u_a::text, u_b::text, u_c::text FROM feature_vectors ORDER BY file_id').fetchall()
    for bo, cot in zip('ABC', ['u_a', 'u_b', 'u_c']):
        V = np.array([json.loads(r[cot]) for r in hang])
        assert np.allclose(V, db.U[bo], atol=1e-6)  # pgvector lưu float32


def test_pgvector_giong_vet_can(db):
    for bo in 'ABC':
        for i in range(0, len(db.ma), 25):
            m = db.ma[i]
            sql = db.tim_sql(db.U[bo][i], bo, 5, [m])
            vc = tim_tuan_tu(db.U[bo], db.ma, db.U[bo][i], 5, [m])
            assert [x[1] for x in sql] == [x[1] for x in vc]
            assert [x[0] for x in sql] == [x[0] for x in vc]  # khoảng cách tính lại bằng số thực 64 bit


def test_truy_van_trung_tep_trong_kho_bi_bo(db):
    t = db.tep[db.ma[10]]
    kq = db.tim_kiem(REPO / 'filtered_output' / t['duong_dan'])
    assert kq['trung_tep_trong_kho'] == [t['ma_tep']]
    assert len(kq['ket_qua']) == 5 and t['ma_tep'] not in [r['ma_tep'] for r in kq['ket_qua']]
    d = [r['khoang_cach'] for r in kq['ket_qua']]
    assert d == sorted(d)
    # Kết quả trung gian (Yêu cầu 4b): 60 giá trị z và d_C² = ½d_A² + ½d_B² cho từng kết quả
    assert [x['chieu'] for x in kq['trung_gian']][20:22] == ['A21', 'B1'] and len(kq['trung_gian']) == 60
    for r in kq['ket_qua']:
        dd = r['khoang_cach_theo_bo']
        assert dd['C'] == pytest.approx(r['khoang_cach']) and dd['C'] ** 2 == pytest.approx((dd['A'] ** 2 + dd['B'] ** 2) / 2)


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


@pytest.mark.parametrize('ten, sua, thong_bao', [
    ('nho', lambda y: y * 0.005, 'dBFS'),                                 # đỉnh khoảng −46 dBFS
    ('mat_khoi_am', lambda y: y[np.argmax(np.abs(y)):], 'mẫu đầu'),       # cắt mất phần trước đỉnh
    ('cat_duoi', lambda y: y[:int(np.argmax(np.abs(y))) + 800], 'cuối'),  # cắt ngay sau đỉnh 50 ms
    ('cat_dinh', lambda y: np.clip(y * 20, -1, 1), 'cắt đỉnh'),
])
def test_truy_van_khong_dat_dieu_kien_muc_2_bi_tu_choi(db, tmp, ten, sua, thong_bao):
    t = db.tep[db.ma[300]]
    y, sr = sf.read(str(REPO / 'filtered_output' / t['duong_dan']))
    sf.write(str(tmp / f'{ten}.wav'), sua(y), sr, subtype='FLOAT')
    with pytest.raises(LoiAmThanh, match=thong_bao):
        db.tim_kiem(tmp / f'{ten}.wav')


def test_rang_buoc_csdl_chan_tep_khong_dat_muc_2(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.con.execute('UPDATE signal_checks SET peak_dbfs = -50 WHERE file_id = %s', (int(db.ma[0]),))


def test_nhac_cu_ngoai_13_lop_van_tra_ve_5_ket_qua(db, tmp):
    t = np.arange(16000) / 16000
    chuong = sum(np.sin(2 * np.pi * f * t) for f in [880, 2390, 4100]) * np.exp(-4 * t)
    sf.write(str(tmp / 'chuong.wav'), chuong / 4, 16000)
    assert len(db.tim_kiem(tmp / 'chuong.wav', 'A')['ket_qua']) == 5
