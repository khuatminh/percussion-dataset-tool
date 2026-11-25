#!/usr/bin/env python3
"""Đánh giá tìm kiếm top 5 cho ba bộ A, B, C và kiểm chứng cây k-d.

Các phép đánh giá:
  1. Kiểm chứng: đặc trưng trong CSDL khớp bảng đặc trưng của báo cáo; cây k-d và truy vấn pgvector
     cho đúng kết quả vét cạn; độ phủ top-5 của chỉ mục HNSW khi bắt buộc dùng chỉ mục.
  2. Bỏ-một-ra (leave-one-out): mỗi tệp lần lượt làm truy vấn, tìm trong 654 tệp còn lại.
  3. Chia theo nhóm bản thu (5 phần): tệp kiểm tra không cùng nhóm bản thu với tệp nào trong kho;
     μ, s chỉ tính trên phần xây dựng.
  4. Độ bền: truy vấn là bản biến đổi của tệp trong kho (giảm âm lượng, stereo 44,1 kHz, thêm nhiễu, MP3).
  5. Nhạc cụ ngoài kho: phân bố nhãn và họ nhạc cụ (Bảng 1 của báo cáo) trong 5 kết quả; không có
     đáp án đúng nên đây là mô tả hành vi, không phải độ chính xác.
  6. Thời gian: tách phần đọc tệp + trích đặc trưng với phần tìm top-5 của từng cách tìm.
Chạy từ thư mục gốc repo:  python csdl_tim_kiem/danh_gia.py
"""
import csv
import json
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from cay_kd import CayKD, tim_tuan_tu
from csdl import CSDL
from csdl import _vec
from dac_trung import A_NAMES, B_NAMES, REPO, LoiAmThanh, tham_so_chuan_hoa, vector_u

RA = Path(__file__).resolve().parent / 'ket_qua_danh_gia'
K = 5
SO_PHAN = 5
TRUY_VAN_THU = Path(__file__).resolve().parent / 'truy_van_thu'
# Họ nhạc cụ theo Bảng 1 của báo cáo; nhạc cụ ngoài kho được xếp vào họ tương ứng nếu có.
HO = {'mang_rung': ['kick', 'tom', 'conga', 'snare', 'djembe', 'bongo', 'tabla'],
      'kim_loai': ['hi_hat', 'cymbal', 'cowbell', 'agogo', 'tambourine', 'gong', 'triangle'],
      'go': ['claves', 'castanets', 'woodblock', 'cajon'],
      'thanh_go': ['marimba', 'xylophone', 'vibraphone']}
HO_CUA = {n: h for h, ds in HO.items() for n in ds}


def chi_so(nhan_tv, nhan_kq):
    """P@5, đúng ở hạng 1, và bỏ phiếu đa số trong 5 kết quả (hòa thì lấy nhãn gặp trước)."""
    dung = [n == nhan_tv for n in nhan_kq]
    dem = defaultdict(int)
    for n in nhan_kq:
        dem[n] += 1
    phieu = max(dem, key=lambda n: (dem[n], -nhan_kq.index(n)))
    return dict(p5=sum(dung) / len(dung), top1=float(dung[0]), bau=float(phieu == nhan_tv))


def tong_hop(dong, lop):
    """Trung bình trên mọi truy vấn, và trung bình của các lớp (mỗi lớp trọng số như nhau)."""
    kq = {}
    for m in ['p5', 'top1', 'bau']:
        kq[m + '_moi_truy_van'] = float(np.mean([d[m] for d in dong]))
        theo_lop = [np.mean([d[m] for d in dong if d['nhan'] == c]) for c in lop if any(d['nhan'] == c for d in dong)]
        kq[m + '_trung_binh_lop'] = float(np.mean(theo_lop))
    kq['so_truy_van'] = len(dong)
    return kq


def kiem_chung(db):
    fa = list(csv.DictReader((REPO / 'filtered_output/features/features_A.csv').open(encoding='utf-8-sig')))
    fb = list(csv.DictReader((REPO / 'filtered_output/features/features_B.csv').open(encoding='utf-8-sig')))
    X = np.c_[[[float(r[n]) for n in A_NAMES] for r in fa], [[float(r[n]) for n in B_NAMES] for r in fb]]
    assert [int(r['sample_id']) for r in fa] == list(db.ma)
    lech = float(np.max(np.abs(db.goc - X) / np.maximum(np.abs(X), 1e-9)))
    fc = list(csv.DictReader((REPO / 'filtered_output/features/features_C_standardized.csv').open(encoding='utf-8-sig')))
    lech_c = float(np.max(np.abs(db.U['C'] - [[float(r[n]) for n in A_NAMES + B_NAMES] for r in fc])))
    kd, pg = {}, {}
    for bo in 'ABC':
        khop, phep, pg_khop, pg_cung_tap = 0, [], 0, 0
        for i, m in enumerate(db.ma):
            a = db.cay[bo].tim(db.U[bo][i], K, [m])
            phep.append(db.cay[bo].so_phep_tinh)
            b = tim_tuan_tu(db.U[bo], db.ma, db.U[bo][i], K, [m])
            khop += [x[1] for x in a] == [x[1] for x in b] and np.allclose([x[0] for x in a], [x[0] for x in b])
            c = db.tim_sql(db.U[bo][i], bo, K, [m])  # pgvector: số thực 32 bit, chỉ mục HNSW (xấp xỉ)
            pg_khop += [x[1] for x in c] == [x[1] for x in b] and [x[0] for x in c] == [x[0] for x in b]
            pg_cung_tap += {x[1] for x in c} == {x[1] for x in b}
        kd[bo] = dict(truy_van_khop=int(khop), tong=len(db.ma), phep_tinh_tb=float(np.mean(phep)))
        pg[bo] = dict(cung_thu_tu=int(pg_khop), cung_tap_5_tep=int(pg_cung_tap), tong=len(db.ma))
    return dict(sai_so_tuong_doi_lon_nhat_so_voi_bang_bao_cao=lech, sai_so_lon_nhat_u_C_so_voi_bang_C=lech_c,
                cay_kd_so_voi_vet_can=kd,
                pgvector_so_voi_vet_can=pg)


def bo_mot_ra(db, nhan, lop):
    kq, dong_lop = {}, []
    for bo in 'ABC':
        dong = []
        for i, m in enumerate(db.ma):
            res = db.cay[bo].tim(db.U[bo][i], K, [m])
            dong.append(dict(nhan=nhan[i], **chi_so(nhan[i], [nhan[np.searchsorted(db.ma, r[1])] for r in res])))
        kq[bo] = tong_hop(dong, lop)
        for c in lop:
            d = [x for x in dong if x['nhan'] == c]
            dong_lop.append(dict(danh_gia='bo_mot_ra', bo=bo, lop=c, so_tep=len(d),
                                 p5=np.mean([x['p5'] for x in d]), top1=np.mean([x['top1'] for x in d])))
    return kq, dong_lop


def chia_phan(nhom):
    """Gán mỗi nhóm bản thu vào một trong 5 phần, nhóm lớn trước, vào phần đang ít tệp nhất."""
    dem = defaultdict(int)
    for g in nhom:
        dem[g] += 1
    phan, co = {}, [0] * SO_PHAN
    for g in sorted(dem, key=lambda g: (-dem[g], g)):
        j = int(np.argmin(co))
        phan[g] = j
        co[j] += dem[g]
    return np.array([phan[g] for g in nhom])


def theo_nhom_ban_thu(db, nhan, nhom, lop):
    phan = chia_phan(nhom)
    kq, dong_lop = {}, []
    thieu_lop = []
    for bo in 'ABC':
        dong = []
        for j in range(SO_PHAN):
            xd, kt = phan != j, phan == j
            mu_a, s_a = tham_so_chuan_hoa(db.goc[xd, :21])
            mu_b, s_b = tham_so_chuan_hoa(db.goc[xd, 21:])
            U = vector_u(db.goc[:, :21], db.goc[:, 21:], mu_a, s_a, mu_b, s_b)[bo]
            cay = CayKD(U[xd], db.ma[xd])
            lop_xd = set(nhan[xd])
            for i in np.flatnonzero(kt):
                if nhan[i] not in lop_xd:  # cả lớp nằm trong phần kiểm tra: không thể tìm đúng
                    if bo == 'A':
                        thieu_lop.append(nhan[i])
                    continue
                res = cay.tim(U[i], K)
                dong.append(dict(nhan=nhan[i], **chi_so(nhan[i], [nhan[np.searchsorted(db.ma, r[1])] for r in res])))
        kq[bo] = tong_hop(dong, lop)
        for c in lop:
            d = [x for x in dong if x['nhan'] == c]
            if d:
                dong_lop.append(dict(danh_gia='theo_nhom_ban_thu', bo=bo, lop=c, so_tep=len(d),
                                     p5=np.mean([x['p5'] for x in d]), top1=np.mean([x['top1'] for x in d])))
    kq['so_tep_moi_phan'] = np.bincount(phan).tolist()
    kq['so_nhom_ban_thu'] = len(set(nhom))
    kq['truy_van_bi_bo_vi_lop_khong_co_trong_kho'] = {c: thieu_lop.count(c) for c in sorted(set(thieu_lop))}
    return kq, dong_lop


def bien_doi(y, kieu, rng):
    if kieu == 'giam_20dB':
        return y * 0.1, 16000
    if kieu == 'stereo_44k1':
        z = resample_poly(y, 441, 160)
        return np.c_[z, 0.8 * z], 44100
    if kieu == 'nhieu_30dB':
        p = np.mean(y ** 2)
        return y + rng.normal(scale=np.sqrt(p / 1000), size=len(y)), 16000
    if kieu == 'mp3_44k1':
        return resample_poly(y, 441, 160), 44100
    raise ValueError(kieu)


def do_ben(db, nhan):
    kieu_ds = ['giam_20dB', 'stereo_44k1', 'nhieu_30dB', 'mp3_44k1']
    rng = np.random.default_rng(7)
    kq = {}
    with tempfile.TemporaryDirectory() as tmp:
        for kieu in kieu_ds:
            hang_cua_ban_goc = {bo: [] for bo in 'ABC'}
            p5 = {bo: [] for bo in 'ABC'}
            loi = 0
            for i, m in enumerate(db.ma):
                y, _ = sf.read(str(REPO / 'filtered_output' / db.tep[m]['duong_dan']), dtype='float64')
                z, sr = bien_doi(y, kieu, rng)
                p = Path(tmp) / (f'q.mp3' if kieu.startswith('mp3') else 'q.wav')
                peak = np.max(np.abs(z))
                if peak > 1:
                    z = z / peak
                try:
                    if kieu.startswith('mp3'):
                        sf.write(str(p), z, sr, format='MP3')
                    else:
                        sf.write(str(p), z, sr, subtype='PCM_16')
                    tv = db.vector_truy_van(p)
                except Exception:
                    loi += 1
                    continue
                for bo in 'ABC':
                    res = db.cay[bo].tim(tv['u'][bo], K + 1)
                    ma_kq = [r[1] for r in res]
                    hang_cua_ban_goc[bo].append(ma_kq.index(m) + 1 if m in ma_kq else K + 2)
                    con_lai = [x for x in ma_kq if x != m][:K]
                    p5[bo].append(np.mean([nhan[np.searchsorted(db.ma, x)] == nhan[i] for x in con_lai]))
            kq[kieu] = {bo: dict(ban_goc_o_hang_1=float(np.mean(np.array(hang_cua_ban_goc[bo]) == 1)),
                                 ban_goc_trong_top5=float(np.mean(np.array(hang_cua_ban_goc[bo]) <= K)),
                                 p5_khong_tinh_ban_goc=float(np.mean(p5[bo])))
                        for bo in 'ABC'}
            kq[kieu]['loi_doc_ghi'] = loi
    return kq


def hnsw(db):
    """Bắt buộc PostgreSQL dùng chỉ mục HNSW (tìm xấp xỉ) và đo độ phủ top-5 so với vét cạn."""
    kq = {}
    db.con.execute('SET enable_seqscan = off')
    try:
        for bo in 'ABC':
            cot, dung = 'u_' + bo.lower(), 0
            for i, m in enumerate(db.ma):
                hang = db.con.execute(f'SELECT file_id FROM feature_vectors WHERE file_id <> %s '
                                      f'ORDER BY {cot} <-> %s::vector LIMIT {K}', (int(m), _vec(db.U[bo][i])))
                vc = {x[1] for x in tim_tuan_tu(db.U[bo], db.ma, db.U[bo][i], K, [m])}
                dung += len({r['file_id'] for r in hang} & vc)
            kq[bo] = dung / (K * len(db.ma))
        kq['ke_hoach'] = ke_hoach(db)
    finally:
        db.con.execute('RESET enable_seqscan')
    kq['ke_hoach_mac_dinh'] = ke_hoach(db)
    return kq


def ke_hoach(db):
    """Nút quét bảng trong kế hoạch thực thi của truy vấn top-5 bộ C (quét tuần tự hay chỉ mục HNSW)."""
    hang = db.con.execute(f'EXPLAIN SELECT file_id FROM feature_vectors ORDER BY u_c <-> %s::vector LIMIT {K}',
                          (_vec(db.U['C'][0]),)).fetchall()
    return next(r['QUERY PLAN'].strip(' ->') for r in hang if 'Scan' in r['QUERY PLAN'])


def ngoai_kho(db):
    """Truy vấn bằng tệp nhạc cụ không có trong kho: nhãn và họ của 5 kết quả theo từng bộ."""
    ds = [r for r in csv.DictReader((TRUY_VAN_THU / 'danh_sach.csv').open(encoding='utf-8-sig'))
          if r['nhom'] == 'ngoai_kho']
    kq = {'so_tep': len(ds), 'bi_tu_choi': {}, 'theo_nhac_cu': {}}
    for r in ds:
        try:
            tv = db.vector_truy_van(TRUY_VAN_THU / r['duong_dan'])
        except LoiAmThanh as e:
            kq['bi_tu_choi'][r['duong_dan']] = str(e)
            continue
        nc = kq['theo_nhac_cu'].setdefault(r['nhan_metadata'], {'so_truy_van': 0, 'ho': HO_CUA.get(r['nhan_metadata'])})
        nc['so_truy_van'] += 1
        for bo in 'ABC':
            nhan = [db.tep[m]['nhan'] for _, m in db.tim_sql(tv['u'][bo], bo, K)]
            dem = nc.setdefault(f'nhan_{bo}', {})
            for n in nhan:
                dem[n] = dem.get(n, 0) + 1
            if nc['ho']:
                nc.setdefault(f'cung_ho_{bo}', 0)
                nc[f'cung_ho_{bo}'] += sum(HO_CUA[n] == nc['ho'] for n in nhan)
    for nc in kq['theo_nhac_cu'].values():
        for bo in 'ABC':
            nc[f'nhan_{bo}'] = dict(sorted(nc[f'nhan_{bo}'].items(), key=lambda x: -x[1]))
            if nc['ho']:
                nc[f'cung_ho_{bo}'] /= K * nc['so_truy_van']
    return kq


def thoi_gian(db):
    """Trung vị (ms) trên 100 tệp: đọc + kiểm tra + trích đặc trưng, và riêng bước tìm top-5 bộ C."""
    rng = np.random.default_rng(3)
    mau = rng.choice(len(db.ma), 100, replace=False)
    t = {'trich_dac_trung': [], 'pgvector': [], 'cay_kd': [], 'vet_can': []}
    for i in mau:
        m = db.ma[i]
        t0 = time.perf_counter()
        tv = db.vector_truy_van(REPO / 'filtered_output' / db.tep[m]['duong_dan'])
        t['trich_dac_trung'].append(time.perf_counter() - t0)
        q = tv['u']['C']
        for cach, f in [('pgvector', lambda: db.tim_sql(q, 'C', K, [m])),
                        ('cay_kd', lambda: db.cay['C'].tim(q, K, [m])),
                        ('vet_can', lambda: tim_tuan_tu(db.U['C'], db.ma, q, K, [m]))]:
            t0 = time.perf_counter()
            f()
            t[cach].append(time.perf_counter() - t0)
    return {k: round(float(np.median(v)) * 1000, 2) for k, v in t.items()}


def main():
    RA.mkdir(exist_ok=True)
    db = CSDL()
    nhan = np.array([db.tep[m]['nhan'] for m in db.ma])
    nhom = np.array([db.tep[m]['nhom_ban_thu'] for m in db.ma])
    lop = sorted(set(nhan))
    kq = {'kiem_chung': kiem_chung(db)}
    kq['bo_mot_ra'], l1 = bo_mot_ra(db, nhan, lop)
    kq['theo_nhom_ban_thu'], l2 = theo_nhom_ban_thu(db, nhan, nhom, lop)
    kq['do_ben'] = do_ben(db, nhan)
    kq['hnsw_bat_buoc'] = hnsw(db)
    kq['ngoai_kho'] = ngoai_kho(db)
    kq['thoi_gian_trung_vi_ms'] = thoi_gian(db)
    (RA / 'tong_hop.json').write_text(json.dumps(kq, ensure_ascii=False, indent=2))
    with (RA / 'theo_lop.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['danh_gia', 'bo', 'lop', 'so_tep', 'p5', 'top1'])
        w.writeheader()
        w.writerows({**r, 'p5': round(r['p5'], 4), 'top1': round(r['top1'], 4)} for r in l1 + l2)
    print(json.dumps(kq, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
