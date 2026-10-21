"""Đọc âm thanh và tính đặc trưng A/B/C đúng như Mục 9-10 của báo cáo Yêu cầu 1-2.

Hàm tính đặc trưng được dùng lại nguyên văn từ bao_cao_bo_go/trich_xuat_dac_trung.py,
nên các số lưu trong CSDL khớp với các bảng đã nêu trong báo cáo.
"""
import hashlib
import sys
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'bao_cao_bo_go'))
import trich_xuat_dac_trung as _goc  # noqa: E402

SR = 16000
THOI_LUONG_TOI_THIEU = 0.1  # giây, cùng ngưỡng với tiêu chí tuyển chọn (Mục 2)
A_NAMES = list(_goc.A_NAMES)
B_NAMES = list(_goc.B_NAMES)
DIM = {'A': 21, 'B': 39, 'C': 60}

# Tên tiếng Việt của 21 thuộc tính bộ A, theo Phụ lục, dùng khi giải thích kết quả.
_TEN_PHO = {'centroid_hz': 'trọng tâm phổ', 'bandwidth_hz': 'độ rộng phổ', 'rolloff85_hz': 'tần số cắt 85%',
            'flatness': 'độ phẳng phổ', 'entropy': 'entropy phổ', 'zcr': 'tỷ lệ đổi dấu',
            'low500_ratio': 'tỷ lệ năng lượng dưới 500 Hz', 'flux': 'thông lượng phổ'}
TEN_A = ['thời gian có tín hiệu', 'khoảng chứa 90% năng lượng', 'hệ số đỉnh', 'tỷ lệ có tín hiệu',
         'vị trí đỉnh bao RMS'] + [f"{'TB' if s == 'mean' else 'ĐLC'} {_TEN_PHO[n]}"
                                  for n in _goc.SPEC for s in ['mean', 'std']]
TEN_B = [f'TB MFCC {i}' for i in range(1, 14)] + [f'ĐLC MFCC {i}' for i in range(1, 14)] \
    + [f'ĐLC delta MFCC {i}' for i in range(1, 14)]


class LoiAmThanh(ValueError):
    """Tệp không dùng được để tính đặc trưng (im lặng, quá ngắn, không đọc được)."""


def doc_am_thanh(duong_dan):
    """Đọc tệp bất kỳ định dạng libsndfile hỗ trợ, đưa về mono 16 kHz, số thực 64-bit."""
    try:
        y, sr = sf.read(str(duong_dan), dtype='float64', always_2d=True)
    except Exception as e:  # soundfile ném nhiều loại lỗi khác nhau
        raise LoiAmThanh(f'Không đọc được tệp âm thanh: {e}') from e
    y = y.mean(axis=1)  # trộn các kênh thành một kênh
    if sr != SR:
        g = gcd(SR, sr)
        y = resample_poly(y, SR // g, sr // g)
    return y


def ma_bam_pcm(y):
    """Mã băm của tín hiệu sau khi đưa về mono 16 kHz, lượng tử 16 bit; dùng để nhận ra truy vấn trùng tệp trong kho."""
    pcm = np.clip(np.round(y * 32768), -32768, 32767).astype('<i2')
    return hashlib.sha256(pcm.tobytes()).hexdigest()


def tinh_dac_trung(y):
    """Bước 2-6: trả về (21 giá trị gốc bộ A, 39 giá trị gốc bộ B)."""
    if len(y) < THOI_LUONG_TOI_THIEU * SR:
        raise LoiAmThanh(f'Tệp quá ngắn ({len(y) / SR:.3f} s < {THOI_LUONG_TOI_THIEU} s)')
    try:
        a, b, _ = _goc.extract(y)
    except ValueError as e:  # 'Silent signal' hoặc 'No active samples'
        raise LoiAmThanh('Tệp im lặng hoặc không có khối 10 ms nào có RMS > 0,01') from e
    return a, b


def tham_so_chuan_hoa(X):
    """μ_j và s_j (độ lệch chuẩn tổng thể); s_j < 1e-12 thay bằng 1 (Mục 10.1)."""
    mu = X.mean(axis=0)
    s = X.std(axis=0)
    s[s < 1e-12] = 1
    return mu, s


def vector_u(a, b, mu_a, s_a, mu_b, s_b):
    """Vector dùng để tính khoảng cách: u_A, u_B, u_C. Nhận một hàng hoặc ma trận nhiều hàng."""
    za = (np.asarray(a) - mu_a) / s_a
    zb = (np.asarray(b) - mu_b) / s_b
    return {'A': za / np.sqrt(21), 'B': zb / np.sqrt(39),
            'C': np.concatenate([za / np.sqrt(42), zb / np.sqrt(78)], axis=-1)}
