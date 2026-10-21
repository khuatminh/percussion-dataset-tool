#!/usr/bin/env python3
"""Vẽ hai hình minh họa cho báo cáo; chỉ đọc audio và bảng đặc trưng, không sửa dữ liệu.

Hình 1: dạng sóng và phổ đồ của tệp đại diện từng nhóm (evidence/representative_files.csv).
Hình 2: trọng tâm phổ và độ phẳng phổ của 655 tệp (features/features_A.csv).
"""
import csv
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import windows
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / 'filtered_output'
OUT = HERE / 'hinh'
ORDER = ['kick', 'tom', 'conga', 'snare', 'hi_hat', 'cymbal', 'tambourine',
         'cowbell', 'agogo', 'claves', 'marimba', 'xylophone', 'vibraphone']
# Bốn họ theo Bảng 2 của báo cáo; màu giữ cố định theo họ, kèm hình dạng điểm khác nhau.
FAMILY = {'kick': 0, 'tom': 0, 'conga': 0, 'snare': 0,
          'hi_hat': 1, 'cymbal': 1, 'tambourine': 1, 'cowbell': 1, 'agogo': 1,
          'claves': 2,
          'marimba': 3, 'xylophone': 3, 'vibraphone': 3}
FAMILY_NAME = ['Màng rung', 'Tự thân vang, kim loại', 'Tự thân vang, gỗ', 'Thanh gõ có cao độ xác định']
COLORS = ['#2a78d6', '#eb6834', '#eda100', '#1baf7a']
MARKERS = ['o', 's', 'D', '^']
INK, MUTED = '#2b2b29', '#6b6a63'
MAX_S = 2.0
LABEL_OFFSET = {'conga': (5, -10), 'snare': (-30, 4)}

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5, 'axes.edgecolor': MUTED,
                     'axes.linewidth': .5, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'xtick.major.width': .5, 'ytick.major.width': .5, 'axes.labelcolor': INK})


def display(label):
    return label.replace('_', '-')


def read_csv(path):
    with path.open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def spectrogram_db(y):
    # Cùng khung với bộ đặc trưng: 400 mẫu, bước 160, FFT 512, Hann tuần hoàn.
    y = np.pad(y, (0, max(0, 400 - len(y))))
    frames = np.lib.stride_tricks.sliding_window_view(y, 400)[::160]
    P = np.abs(np.fft.rfft(frames * windows.hann(400, sym=False), n=512, axis=1)) ** 2
    return 10 * np.log10(np.maximum(P / P.max(), 1e-8)).T


def figure_spectrograms():
    reps = {r['label']: r for r in read_csv(ROOT / 'evidence/representative_files.csv')}
    fig = plt.figure(figsize=(7.1, 8.4))
    outer = fig.add_gridspec(4, 4, hspace=.5, wspace=.32, left=.06, right=.99, top=.97, bottom=.04)
    image = None
    for i, label in enumerate(ORDER):
        rep = reps[label]
        y, sr = sf.read(ROOT / rep['relative_path'], dtype='float64')
        y = y - y.mean()
        y = y / np.max(np.abs(y))
        y = y[:int(MAX_S * sr)]
        dur = len(y) / sr
        cell = outer[i // 4, i % 4].subgridspec(2, 1, height_ratios=[1, 2.6], hspace=.08)
        ax_w = fig.add_subplot(cell[0])
        ax_s = fig.add_subplot(cell[1], sharex=ax_w)
        ax_w.plot(np.arange(len(y)) / sr, y, color=INK, lw=.4)
        ax_w.set_ylim(-1.05, 1.05)
        ax_w.set_yticks([])
        ax_w.tick_params(labelbottom=False, length=0)
        for side in ['top', 'right', 'left']:
            ax_w.spines[side].set_visible(False)
        note = f' (2 s đầu / {float(rep["duration_s"]):.1f} s)'.replace('.', ',') if float(rep['duration_s']) > MAX_S else ''
        ax_w.set_title(f'{display(label)}{note}', fontsize=7.5, color=INK, loc='left', pad=2)
        S = spectrogram_db(y)
        image = ax_s.imshow(S, origin='lower', aspect='auto', cmap='Blues', vmin=-80, vmax=0,
                            extent=[0, max(dur, 400 / sr), 0, 8], rasterized=True, interpolation='nearest')
        ax_s.set_xlim(0, max(dur, 400 / sr))
        ax_s.set_yticks([0, 2, 4, 6, 8])
        ax_s.tick_params(length=2, pad=1.5, labelsize=6.5)
        if i % 4 == 0:
            ax_s.set_ylabel('kHz', labelpad=1)
        ax_s.set_xlabel('giây', labelpad=1, fontsize=6.5)
    cax = fig.add_axes([.32, .135, .4, .012])
    bar = fig.colorbar(image, cax=cax, orientation='horizontal')
    bar.set_label('Công suất so với cực đại của tệp (dB)', fontsize=7)
    bar.outline.set_linewidth(.4)
    bar.ax.tick_params(labelsize=6.5, length=2)
    fig.savefig(OUT / 'hinh1_song_va_pho.pdf', dpi=220)
    plt.close(fig)


def figure_scatter():
    rows = read_csv(ROOT / 'features/features_A.csv')
    labels = np.array([r['label'] for r in rows])
    x = np.array([float(r['centroid_hz_mean']) for r in rows])
    y = np.array([float(r['flatness_mean']) for r in rows])
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for fam in range(len(FAMILY_NAME)):
        m = np.array([FAMILY[l] == fam for l in labels])
        ax.scatter(x[m], y[m], s=9, marker=MARKERS[fam], color=COLORS[fam], alpha=.28,
                   linewidths=0, label=FAMILY_NAME[fam], rasterized=True)
    for label in ORDER:
        m = labels == label
        fam = FAMILY[label]
        mx, my = np.median(x[m]), np.median(y[m])
        ax.scatter([mx], [my], s=46, marker=MARKERS[fam], color=COLORS[fam],
                   edgecolors='white', linewidths=1.2, zorder=3)
        ax.annotate(display(label), (mx, my), xytext=LABEL_OFFSET.get(label, (5, 3)), textcoords='offset points', fontsize=7.5,
                    color=INK, zorder=4)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Trọng tâm phổ trung bình theo khung (Hz, thang log)')
    ax.set_ylabel('Độ phẳng phổ trung bình (thang log)')
    ax.grid(True, which='major', color='#e4e3dd', lw=.5)
    ax.set_axisbelow(True)
    for side in ['top', 'right']:
        ax.spines[side].set_visible(False)
    legend = ax.legend(loc='lower right', fontsize=7, frameon=False, markerscale=1.6)
    for handle in legend.legend_handles:
        handle.set_alpha(1)
    fig.tight_layout()
    fig.savefig(OUT / 'hinh2_trong_tam_do_phang.pdf', dpi=220)
    plt.close(fig)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    figure_spectrograms()
    figure_scatter()
    print('Đã ghi', *sorted(p.name for p in OUT.glob('*.pdf')))
