#!/usr/bin/env python3
"""Đánh giá bổ sung cho Yêu cầu 4c, chạy KHÔNG cần PostgreSQL (tìm vét cạn bằng NumPy).

Vét cạn cho đúng cùng danh sách top-5 với pgvector và cây k-d (đã kiểm chứng trong danh_gia.py),
nên các số dưới đây áp dụng cho hệ thống thật. Bổ sung cho danh_gia.py các chỉ số:

  1. Chỉ số xếp hạng: P@5, AP@5 (mAP@5), MRR (hạng của kết quả đúng đầu tiên trên toàn kho),
     nDCG@5 có phân mức (cùng nhạc cụ = 2, cùng họ nhạc cụ = 1, khác họ = 0), P@5 theo họ nhạc cụ.
     Tính cho bỏ-một-ra và chia theo nhóm bản thu (giống danh_gia.py).
  2. Ma trận nhầm lẫn: nhãn truy vấn × nhãn của 5 kết quả (bộ C, chia theo nhóm bản thu).
  3. Phân bố khoảng cách d1 (tới kết quả hạng 1): truy vấn nhạc cụ đã có (loại các tệp cùng nhóm bản thu)
     so với 69 truy vấn nhạc cụ ngoài kho; AUC và ngưỡng cảnh báo "có thể là nhạc cụ chưa có trong kho".
  4. Kết quả của 4 tệp mới thuộc lớp đã có (truy_van_thu/trong_lop).

Chạy từ thư mục gốc repo:  python csdl_tim_kiem/danh_gia_bo_sung.py
Kết quả: csdl_tim_kiem/ket_qua_danh_gia/bo_sung.json, nham_lan_C.csv và 2 hình trong bao_cao_bo_go/hinh/.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from dac_trung import LoiAmThanh, REPO, doc_am_thanh, tham_so_chuan_hoa, tinh_dac_trung, vector_u

K = 5
DU_LIEU = REPO / 'filtered_output'
RA = Path(__file__).resolve().parent / 'ket_qua_danh_gia'
HINH = REPO / 'bao_cao_bo_go' / 'hinh'
TRUY_VAN_THU = Path(__file__).resolve().parent / 'truy_van_thu'
SO_PHAN = 5
# Ba khối dưới đây chép từ danh_gia.py và xay_dung_csdl.py để tệp này chạy được khi không có PostgreSQL.
HO = {'mang_rung': ['kick', 'tom', 'conga', 'snare', 'djembe', 'bongo', 'tabla'],
      'kim_loai': ['hi_hat', 'cymbal', 'cowbell', 'agogo', 'tambourine', 'gong', 'triangle'],
      'go': ['claves', 'castanets', 'woodblock', 'cajon'],
      'thanh_go': ['marimba', 'xylophone', 'vibraphone']}
HO_CUA = {n: h for h, ds in HO.items() for n in ds}


def nguon_va_nhom(r):
    url = r['collection_url']
    if 'idmt' in url:
        return 'IDMT', 'idmt:' + r['source_name'].split('_')[0]
    if 'uiowa' in url:
        return 'Iowa', 'iowa:' + r['source_original_metadata_path'].split('/')[-2]
    return 'Freesound', 'freesound:' + r['uploader']


def chia_phan(nhom):
    dem = defaultdict(int)
    for g in nhom:
        dem[g] += 1
    phan, co = {}, [0] * SO_PHAN
    for g in sorted(dem, key=lambda g: (-dem[g], g)):
        j = int(np.argmin(co))
        phan[g] = j
        co[j] += dem[g]
    return np.array([phan[g] for g in nhom])


def danh_sach_tep():
    """655 tệp theo thứ tự kiểm kê (evidence/inventory.csv nếu có, không thì theo accepted.csv)."""
    meta = [r for r in csv.DictReader((DU_LIEU / 'accepted.csv').open(encoding='utf-8-sig'))
            if r['status'] == 'accepted']
    ki = DU_LIEU / 'evidence/inventory.csv'
    if ki.exists():
        thu_tu = {r['relative_path']: int(r['index']) for r in csv.DictReader(ki.open(encoding='utf-8-sig'))}
        meta.sort(key=lambda r: thu_tu[r['output']])
    return [dict(duong_dan=m['output'], nhan=m['label'], nhom=nguon_va_nhom(m)[1]) for m in meta]


def dac_trung_kho(tep):
    A, B = [], []
    for t in tep:
        y, _ = doc_am_thanh(DU_LIEU / t['duong_dan'])
        a, b = tinh_dac_trung(y)
        A.append(a)
        B.append(b)
    return np.array(A), np.array(B)


def xep_hang(U_kho, q, loai_tru):
    """Toàn bộ kho xếp theo khoảng cách tăng dần (hòa thì chỉ số nhỏ trước), bỏ các chỉ số trong loai_tru."""
    d = np.linalg.norm(U_kho - q, axis=1)
    d[list(loai_tru)] = np.inf
    thu_tu = np.lexsort((np.arange(len(d)), d))
    thu_tu = thu_tu[np.isfinite(d[thu_tu])]
    return thu_tu, d[thu_tu]


def lien_quan(nhan_tv, nhan_kq):
    """Mức liên quan phân mức: 2 cùng nhạc cụ, 1 cùng họ, 0 khác họ."""
    if nhan_kq == nhan_tv:
        return 2
    h = HO_CUA.get(nhan_tv)
    return 1 if h is not None and HO_CUA.get(nhan_kq) == h else 0


def chi_so_xep_hang(nhan_tv, nhan_xep, so_lien_quan):
    """nhan_xep: nhãn của toàn bộ kho đã xếp hạng; so_lien_quan: số tệp cùng nhãn còn trong kho."""
    dung = np.array([n == nhan_tv for n in nhan_xep])
    top = dung[:K]
    # AP@5: trung bình precision tại các hạng đúng, chia cho min(K, số tệp liên quan)
    ap = sum(top[:i + 1].mean() for i in range(K) if top[i]) / min(K, so_lien_quan)
    hang_dau = int(np.argmax(dung)) + 1 if dung.any() else None
    g = np.array([lien_quan(nhan_tv, n) for n in nhan_xep[:K]], float)
    chiet_khau = 1 / np.log2(np.arange(2, K + 2))
    ly_tuong = np.sort([lien_quan(nhan_tv, n) for n in nhan_xep])[::-1][:K]
    ndcg = float(((2 ** g - 1) * chiet_khau).sum() / max(((2 ** ly_tuong - 1) * chiet_khau).sum(), 1e-12))
    return dict(p5=float(top.mean()), ap5=float(ap), rr=1 / hang_dau if hang_dau else 0.0,
                hang_dung_dau=hang_dau, ndcg5=ndcg, p5_ho=float(np.mean(g >= 1)))


def tong_hop(dong, lop):
    kq = {}
    for m in ['p5', 'ap5', 'rr', 'ndcg5', 'p5_ho']:
        kq[m + '_moi_truy_van'] = float(np.mean([d[m] for d in dong]))
        kq[m + '_trung_binh_lop'] = float(np.mean([np.mean([d[m] for d in dong if d['nhan'] == c])
                                                   for c in lop if any(d['nhan'] == c for d in dong)]))
    kq['hang_dung_dau_trung_vi'] = float(np.median([d['hang_dung_dau'] for d in dong]))
    kq['so_truy_van'] = len(dong)
    return kq


def danh_gia_kho(goc, nhan, nhom, lop):
    """Bỏ-một-ra và chia theo nhóm bản thu; trả về chỉ số và các cặp (nhãn truy vấn, nhãn kết quả)."""
    kq, cap_nham = {}, defaultdict(list)
    mu_a, s_a = tham_so_chuan_hoa(goc[:, :21])
    mu_b, s_b = tham_so_chuan_hoa(goc[:, 21:])
    U_toan = vector_u(goc[:, :21], goc[:, 21:], mu_a, s_a, mu_b, s_b)
    phan = chia_phan(nhom)
    for bo in 'ABC':
        dong = []
        for i in range(len(nhan)):
            tt, _ = xep_hang(U_toan[bo], U_toan[bo][i], [i])
            dong.append(dict(nhan=nhan[i], **chi_so_xep_hang(nhan[i], nhan[tt], int((nhan == nhan[i]).sum()) - 1)))
        kq[f'bo_mot_ra_{bo}'] = tong_hop(dong, lop)
        dong = []
        for j in range(phan.max() + 1):
            xd = np.flatnonzero(phan != j)
            ma_ = tham_so_chuan_hoa(goc[xd, :21]) + tham_so_chuan_hoa(goc[xd, 21:])
            U = vector_u(goc[:, :21], goc[:, 21:], *ma_)[bo]
            for i in np.flatnonzero(phan == j):
                so = int((nhan[xd] == nhan[i]).sum())
                if so == 0:  # agogo: cả lớp nằm trong phần kiểm tra
                    continue
                tt, _ = xep_hang(U[xd], U[i], [])
                nx = nhan[xd][tt]
                dong.append(dict(nhan=nhan[i], **chi_so_xep_hang(nhan[i], nx, so)))
                cap_nham[bo] += [(nhan[i], n) for n in nx[:K]]
        kq[f'theo_nhom_ban_thu_{bo}'] = tong_hop(dong, lop)
    return kq, cap_nham, U_toan


def ma_tran_nham(cap, lop):
    M = np.zeros((len(lop), len(lop)))
    for a, b in cap:
        M[lop.index(a), lop.index(b)] += 1
    tong = M.sum(axis=1, keepdims=True)
    return np.divide(M, tong, out=np.zeros_like(M), where=tong > 0)  # agogo không có truy vấn: hàng 0


def doc_truy_van_thu():
    ds = []
    for r in csv.DictReader((TRUY_VAN_THU / 'danh_sach.csv').open(encoding='utf-8-sig')):
        try:
            y, _ = doc_am_thanh(TRUY_VAN_THU / r['duong_dan'])
            a, b = tinh_dac_trung(y)
        except LoiAmThanh:
            continue
        ds.append(dict(nhom=r['nhom'], nhan=r['nhan_metadata'], duong_dan=r['duong_dan'], a=a, b=b))
    return ds


def auc(duong, am):
    """Xác suất một giá trị của nhóm dương lớn hơn một giá trị nhóm âm (Mann-Whitney)."""
    duong, am = np.asarray(duong), np.asarray(am)
    return float(((duong[:, None] > am[None]).sum() + .5 * (duong[:, None] == am[None]).sum()) / (len(duong) * len(am)))


def phan_tich_khoang_cach(goc, nhan, nhom, U_toan, truy_van, lop):
    """d1 của truy vấn đã có (loại cả nhóm bản thu của nó) so với truy vấn nhạc cụ ngoài kho."""
    mu_a, s_a = tham_so_chuan_hoa(goc[:, :21])
    mu_b, s_b = tham_so_chuan_hoa(goc[:, 21:])
    kq, d1 = {}, {}
    for bo in 'ABC':
        trong = []
        for i in range(len(nhan)):
            _, d = xep_hang(U_toan[bo], U_toan[bo][i], np.flatnonzero(nhom == nhom[i]))
            trong.append(d[0])
        ngoai = []
        for t in truy_van:
            if t['nhom'] != 'ngoai_kho':
                continue
            q = vector_u(t['a'], t['b'], mu_a, s_a, mu_b, s_b)[bo]
            ngoai.append(xep_hang(U_toan[bo], q, [])[1][0])
        trong, ngoai = np.array(trong), np.array(ngoai)
        nguong = {p: float(np.percentile(trong, p)) for p in (90, 95)}
        kq[bo] = dict(d1_trung_vi_nhac_cu_da_co=float(np.median(trong)), d1_trung_vi_ngoai_kho=float(np.median(ngoai)),
                      auc_phan_biet_ngoai_kho=auc(ngoai, trong),
                      nguong={str(p): dict(gia_tri=v, ty_le_ngoai_kho_bi_canh_bao=float(np.mean(ngoai > v)),
                                           ty_le_da_co_bi_canh_bao=float(np.mean(trong > v)))
                              for p, v in nguong.items()},
                      so_truy_van_da_co=len(trong), so_truy_van_ngoai_kho=len(ngoai))
        d1[bo] = (trong, ngoai)
    return kq, d1


def trong_lop(goc, nhan, tep, truy_van):
    mu_a, s_a = tham_so_chuan_hoa(goc[:, :21])
    mu_b, s_b = tham_so_chuan_hoa(goc[:, 21:])
    U = vector_u(goc[:, :21], goc[:, 21:], mu_a, s_a, mu_b, s_b)['C']
    ra = []
    for t in truy_van:
        if t['nhom'] != 'trong_lop':
            continue
        tt, d = xep_hang(U, vector_u(t['a'], t['b'], mu_a, s_a, mu_b, s_b)['C'], [])
        ra.append(dict(tep=t['duong_dan'], nhan=t['nhan'], ket_qua=[str(nhan[i]) for i in tt[:K]],
                       khoang_cach=[round(float(x), 4) for x in d[:K]],
                       p5=float(np.mean(nhan[tt[:K]] == t['nhan']))))
    return ra


def ve_hinh(M, lop, d1):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 6))
    hang = [i for i in range(len(lop)) if M[i].sum() > 0]  # bỏ hàng agogo (không có truy vấn)
    im = ax.imshow(M[hang], cmap='Blues', vmin=0, vmax=1)
    ax.set_xticks(range(len(lop)), lop, rotation=60, ha='right')
    ax.set_yticks(range(len(hang)), [lop[i] for i in hang])
    M = M[hang]
    for i in range(len(hang)):
        for j in range(len(lop)):
            if M[i, j] >= .05:
                ax.text(j, i, f'{M[i, j]:.2f}'.replace('.', ','), ha='center', va='center', fontsize=7,
                        color='white' if M[i, j] > .5 else 'black')
    ax.set_xlabel('Nhãn của 5 kết quả')
    ax.set_ylabel('Nhãn của truy vấn')
    fig.colorbar(im, fraction=.046)
    fig.tight_layout()
    fig.savefig(HINH / 'hinh7_ma_tran_nham_lan.pdf')
    fig.savefig(HINH / 'hinh7_ma_tran_nham_lan.png', dpi=200)
    plt.close(fig)

    trong, ngoai = d1['C']
    fig, ax = plt.subplots(figsize=(7, 3.4))
    bins = np.linspace(0, max(trong.max(), ngoai.max()), 30)
    ax.hist(trong, bins=bins, density=True, alpha=.6, label=f'Nhạc cụ đã có ({len(trong)} truy vấn)')
    ax.hist(ngoai, bins=bins, density=True, alpha=.6, label=f'Nhạc cụ ngoài kho ({len(ngoai)} truy vấn)')
    ax.axvline(np.percentile(trong, 95), color='k', ls='--', lw=1, label='Ngưỡng phân vị 95')
    ax.set_xlabel('Khoảng cách tới kết quả hạng 1 (bộ C)')
    ax.set_ylabel('Mật độ')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(HINH / 'hinh8_phan_bo_khoang_cach.pdf')
    fig.savefig(HINH / 'hinh8_phan_bo_khoang_cach.png', dpi=200)
    plt.close(fig)


def main():
    RA.mkdir(exist_ok=True)
    tep = danh_sach_tep()
    A, B = dac_trung_kho(tep)
    goc = np.c_[A, B]
    nhan = np.array([t['nhan'] for t in tep])
    nhom = np.array([t['nhom'] for t in tep])
    lop = sorted(str(c) for c in set(nhan))
    kq, cap_nham, U_toan = danh_gia_kho(goc, nhan, nhom, lop)
    M = ma_tran_nham(cap_nham['C'], lop)
    with (RA / 'nham_lan_C.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['truy_van\\ket_qua'] + lop)
        for c, hang in zip(lop, M):
            w.writerow([c] + [f'{x:.3f}' for x in hang])
    kq['nham_lan_lon_nhat_C'] = [dict(truy_van=str(lop[i]), ket_qua=str(lop[j]), ty_le=round(float(M[i, j]), 3))
                                 for i, j in sorted(((i, j) for i in range(len(lop)) for j in range(len(lop)) if i != j),
                                                    key=lambda p: -M[p])[:8]]
    truy_van = doc_truy_van_thu()
    kq['khoang_cach_ngoai_kho'], d1 = phan_tich_khoang_cach(goc, nhan, nhom, U_toan, truy_van, lop)
    kq['tep_moi_lop_da_co'] = trong_lop(goc, nhan, tep, truy_van)
    (RA / 'bo_sung.json').write_text(json.dumps(kq, ensure_ascii=False, indent=2), encoding='utf-8')
    ve_hinh(M, lop, d1)

    print(f"{'Đánh giá':<22}{'Bộ':<4}{'P@5':>7}{'mAP@5':>7}{'MRR':>7}{'nDCG@5':>8}{'P@5 họ':>8}")
    for ten in ['bo_mot_ra', 'theo_nhom_ban_thu']:
        for bo in 'ABC':
            r = kq[f'{ten}_{bo}']
            print(f"{ten:<22}{bo:<4}" + ''.join(f"{r[m + '_moi_truy_van']:>{w}.3f}" for m, w in
                                                [('p5', 7), ('ap5', 7), ('rr', 7), ('ndcg5', 8), ('p5_ho', 8)]))
    for bo, r in kq['khoang_cach_ngoai_kho'].items():
        print(f"d1 bộ {bo}: đã có {r['d1_trung_vi_nhac_cu_da_co']:.3f}, ngoài kho {r['d1_trung_vi_ngoai_kho']:.3f}, "
              f"AUC {r['auc_phan_biet_ngoai_kho']:.3f}, ngưỡng P95 cảnh báo {r['nguong']['95']['ty_le_ngoai_kho_bi_canh_bao']:.2f} ngoài kho")
    print('Nhầm lẫn lớn nhất (C):', kq['nham_lan_lon_nhat_C'][:5])
    for t in kq['tep_moi_lop_da_co']:
        print(t['tep'], t['ket_qua'], t['p5'])


if __name__ == '__main__':
    main()
