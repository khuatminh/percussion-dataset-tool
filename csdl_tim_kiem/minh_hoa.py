#!/usr/bin/env python3
"""Yêu cầu 4b: ghi kết quả trung gian của các truy vấn ví dụ và vẽ hình cho báo cáo.

Ra: ket_qua_danh_gia/minh_hoa.json; bao_cao_bo_go/hinh/hinh{3,4,5}_*.pdf.
Chạy từ thư mục gốc repo (sau xay_dung_csdl.py và danh_gia.py):  python csdl_tim_kiem/minh_hoa.py
"""
import csv
import json
from pathlib import Path

import matplotlib
import numpy as np
import soundfile as sf
from scipy.signal import windows

from csdl import CSDL
from dac_trung import REPO, LoiAmThanh, doc_am_thanh

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

DAY = Path(__file__).resolve().parent
TV = DAY / 'truy_van_thu'
HINH = REPO / 'bao_cao_bo_go/hinh'
VI_DU = {'trong_lop': TV / 'trong_lop/kick/fs185294.wav',
         'ngoai_kho': TV / 'ngoai_kho/djembe/fs54015.wav',
         'bi_tu_choi': TV / 'ngoai_kho/maracas/fs9697.wav'}
INK, MUTED = '#2b2b29', '#6b6a63'
MAU = {'A': '#2a78d6', 'B': '#eb6834', 'C': '#1baf7a'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5, 'axes.edgecolor': MUTED,
                     'axes.linewidth': .5, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'xtick.major.width': .5, 'ytick.major.width': .5, 'axes.labelcolor': INK})


def ghi_vi_du(db, ten, p):
    try:
        tv = db.tim_kiem(p)
    except LoiAmThanh as e:
        return dict(tep=p.relative_to(DAY).as_posix(), tu_choi=str(e))
    q = tv['u']['C']
    ket_qua = []
    for r in tv['ket_qua']:
        i = int(np.searchsorted(db.ma, r['ma_tep']))
        dong_gop = (q - db.U['C'][i]) ** 2  # đóng góp của từng chiều vào d_C²
        lon = np.argsort(-dong_gop)[:5]
        ket_qua.append(dict(hang=r['hang'], ma_tep=r['ma_tep'], nhan=r['nhan'], duong_dan=r['duong_dan'],
                            d=r['khoang_cach_theo_bo'], s=r['do_tuong_dong'], dC2=float(dong_gop.sum()),
                            chieu_dong_gop_lon=[(tv['trung_gian'][j]['chieu'], tv['trung_gian'][j]['ten'],
                                                 float(dong_gop[j])) for j in lon],
                            giai_thich=r['giai_thich']))
    return dict(tep=p.relative_to(DAY).as_posix(), kiem_tra_tin_hieu=tv['kiem_tra_tin_hieu'],
                trung_tep_trong_kho=tv['trung_tep_trong_kho'], dac_trung=tv['trung_gian'], ket_qua=ket_qua)


def pho_do(y):
    # Cùng khung với bộ đặc trưng: 400 mẫu, bước 160, FFT 512, Hann tuần hoàn (như ve_hinh_minh_hoa.py).
    y = np.pad(y / max(np.max(np.abs(y)), 1e-12), (0, max(0, 400 - len(y))))
    khung = np.lib.stride_tricks.sliding_window_view(y, 400)[::160]
    P = np.abs(np.fft.rfft(khung * windows.hann(400, sym=False), n=512, axis=1)) ** 2
    return 10 * np.log10(np.maximum(P / P.max(), 1e-8)).T


def hinh_vi_du(vd, ten_tep):
    """Phổ đồ của truy vấn và 5 kết quả (bộ C)."""
    tep = [(f'Truy vấn ({Path(vd["tep"]).parent.name})', doc_am_thanh(DAY / vd['tep'])[0])]
    for r in vd['ket_qua']:
        y, _ = sf.read(str(REPO / 'filtered_output' / r['duong_dan']), dtype='float64')
        tep.append((f'{r["hang"]}. {r["nhan"].replace("_", "-")}  d = {r["d"]["C"]:.3f}', y))
    fig, truc = plt.subplots(2, 3, figsize=(7.1, 3.6), constrained_layout=True)
    for ax, (tieu_de, y) in zip(truc.flat, tep):
        y = y[:9600]  # 0,6 s đầu, cùng thang thời gian cho mọi ô
        S = pho_do(y)
        ax.imshow(S, origin='lower', aspect='auto', cmap='magma', vmin=-80, vmax=0,
                  extent=[0, S.shape[1] * .01, 0, 8])
        ax.set_xlim(0, .6)
        ax.set_title(tieu_de, fontsize=7.5, color=INK)
        ax.set_xlabel('Thời gian (s)')
        ax.set_ylabel('kHz')
    fig.savefig(HINH / ten_tep)
    plt.close(fig)


def hinh_ho_so_z(vd):
    """Giá trị z của 60 chiều: truy vấn so với kết quả hạng 1 và hạng có nhãn khác (nếu có)."""
    z = np.array([d['z'] for d in vd['dac_trung']])
    db_z = {r['hang']: r for r in vd['ket_qua']}
    fig, ax = plt.subplots(figsize=(7.1, 2.7), constrained_layout=True)
    x = np.arange(60)
    ax.axvspan(-.5, 20.5, color='#f1f3ee', zorder=0)
    ax.plot(x, z, color=INK, lw=1.1, marker='o', ms=2.2, label='Truy vấn')
    for hang, mau in [(1, MAU['C']), (3, MAU['B'])]:
        r = db_z[hang]
        ax.plot(x, r['z'], color=mau, lw=.9, marker='s', ms=1.8,
                label=f'Hạng {hang}: {r["nhan"]} (d = {r["d"]["C"]:.3f})')
    ax.axhline(0, color=MUTED, lw=.4)
    ax.set_xticks([0, 5, 10, 15, 20, 30, 40, 50, 59])
    ax.set_xticklabels(['A1', 'A6', 'A11', 'A16', 'A21', 'B10', 'B20', 'B30', 'B39'])
    ax.set_xlim(-.5, 59.5)
    ax.set_ylabel('z = (x − μ)/s')
    ax.text(10, ax.get_ylim()[1] * .9, 'Bộ A', ha='center', color=MUTED)
    ax.text(40, ax.get_ylim()[1] * .9, 'Bộ B (MFCC)', ha='center', color=MUTED)
    ax.legend(frameon=False, ncol=3, loc='lower center', bbox_to_anchor=(.5, -.42))
    fig.savefig(HINH / 'hinh4_ho_so_z.pdf')
    plt.close(fig)


def hinh_p5_theo_lop():
    dong = [r for r in csv.DictReader((DAY / 'ket_qua_danh_gia/theo_lop.csv').open(encoding='utf-8-sig'))
            if r['danh_gia'] == 'bo_mot_ra']
    lop = sorted({r['lop'] for r in dong}, key=lambda c: -float(next(r['p5'] for r in dong
                                                                      if r['lop'] == c and r['bo'] == 'C')))
    fig, ax = plt.subplots(figsize=(7.1, 2.7), constrained_layout=True)
    x = np.arange(len(lop))
    for k, bo in enumerate('ABC'):
        v = [float(next(r['p5'] for r in dong if r['lop'] == c and r['bo'] == bo)) for c in lop]
        ax.bar(x + (k - 1) * .27, v, .27, color=MAU[bo], label=f'Bộ {bo}')
    ax.set_xticks(x)
    ngan = {'hi_hat': 'hi-hat', 'tambourine': 'tambou-\nrine', 'vibraphone': 'vibra-\nphone', 'xylophone': 'xylo-\nphone'}
    so_tep = {r['lop']: r['so_tep'] for r in dong}
    ax.set_xticklabels([f'{ngan.get(c, c)}\n({so_tep[c]})' for c in lop], fontsize=6.5)
    ax.set_ylabel('P@5 (bỏ-một-ra)')
    ax.set_ylim(0, 1)
    ax.grid(axis='y', color='#e4e4e0', lw=.5)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, ncol=3, loc='upper right')
    fig.savefig(HINH / 'hinh5_p5_theo_lop.pdf')
    plt.close(fig)


def main():
    db = CSDL()
    kq = {ten: ghi_vi_du(db, ten, p) for ten, p in VI_DU.items()}
    for vd in kq.values():  # thêm z của các tệp kết quả để vẽ hồ sơ z
        for r in vd.get('ket_qua', []):
            i = int(np.searchsorted(db.ma, r['ma_tep']))
            r['z'] = np.concatenate([(db.goc[i, :21] - db.mu['A']) / db.s['A'],
                                     (db.goc[i, 21:] - db.mu['B']) / db.s['B']]).tolist()
    (DAY / 'ket_qua_danh_gia/minh_hoa.json').write_text(json.dumps(kq, ensure_ascii=False, indent=1))
    hinh_vi_du(kq['trong_lop'], 'hinh3_vi_du_truy_van.pdf')
    hinh_vi_du(kq['ngoai_kho'], 'hinh6_vi_du_ngoai_kho.pdf')
    hinh_ho_so_z(kq['trong_lop'])
    hinh_p5_theo_lop()
    print('Đã ghi minh_hoa.json và các hình 3-6.')


if __name__ == '__main__':
    main()
