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
    """Tệp không dùng được để tính đặc trưng (không đọc được hoặc không đạt điều kiện chất lượng ở Mục 2)."""


def _so(v, le=3):
    """Số thập phân viết theo kiểu Việt Nam (dấu phẩy), dùng trong thông báo từ chối."""
    return f'{v:.{le}f}'.replace('.', ',')


def kiem_tra_tin_hieu(x, sr):
    """Điều kiện kiểm tra tín hiệu ở Mục 2 (bước 2), áp dụng cho cả tệp trong kho và truy vấn (Mục 10.3).

    x là tín hiệu gốc (mẫu × kênh) trước khi trộn kênh và đổi tần số; cách đo giống kiem_ke_am_thanh.py.
    Trả về các số đo (lưu vào bảng signal_checks), hoặc ném LoiAmThanh kèm mọi điều kiện không đạt.
    """
    if not len(x) or not np.isfinite(x).all():
        raise LoiAmThanh('Tệp rỗng hoặc chứa giá trị không xác định/vô hạn')
    nang_luong = np.mean(x ** 2, axis=1)
    dinh = max(float(np.max(np.abs(x))), 1e-12)
    hop = max(1, round(sr * .01))  # khối 10 ms
    khoi = [(np.sqrt(nang_luong[j:j + hop].mean()), len(nang_luong[j:j + hop])) for j in range(0, len(x), hop)]
    nguong = max(10 ** (-70 / 20), dinh * .01)
    kq = dict(thoi_luong_s=len(x) / sr,
              thoi_gian_co_tieng_s=sum(n for r, n in khoi if r > nguong) / sr,
              dinh_dbfs=20 * np.log10(dinh),
              mau_dau_tuong_doi=np.max(np.abs(x[0])) / dinh,
              cuoi_tuong_doi=khoi[-1][0] / dinh,  # RMS khối 10 ms cuối so với đỉnh
              ty_le_cat_dinh=np.mean(np.abs(x) >= .999))
    kq = {k: float(v) for k, v in kq.items()}
    loi = [m for m, khong_dat in [
        (f'dài {_so(kq["thoi_luong_s"])} s < 0,1 s', kq['thoi_luong_s'] < .1),
        (f'phần có tiếng {_so(kq["thoi_gian_co_tieng_s"])} s < 0,05 s', kq['thoi_gian_co_tieng_s'] < .05),
        (f'đỉnh {_so(kq["dinh_dbfs"], 1)} dBFS < −40 dBFS', kq['dinh_dbfs'] < -40),
        ('mẫu đầu lớn hơn 10% biên độ lớn nhất', kq['mau_dau_tuong_doi'] > .1),
        ('tín hiệu mạnh ở cuối tệp', kq['cuoi_tuong_doi'] > .3),
        ('nghi cắt đỉnh: hơn 1% số mẫu có biên độ ≥ 0,999', kq['ty_le_cat_dinh'] > .01)] if khong_dat]
    if loi:
        raise LoiAmThanh('Không đạt điều kiện chất lượng (Mục 2): ' + '; '.join(loi))
    return kq


def doc_am_thanh(duong_dan):
    """Đọc tệp bất kỳ định dạng libsndfile hỗ trợ, kiểm tra chất lượng, đưa về mono 16 kHz, số thực 64-bit.

    Trả về (tín hiệu mono 16 kHz, số đo kiểm tra tín hiệu).
    """
    try:
        x, sr = sf.read(str(duong_dan), dtype='float64', always_2d=True)
    except Exception as e:  # soundfile ném nhiều loại lỗi khác nhau
        raise LoiAmThanh(f'Không đọc được tệp âm thanh: {e}') from e
    kiem_tra = kiem_tra_tin_hieu(x, sr)
    y = x.mean(axis=1)  # trộn các kênh thành một kênh
    if sr != SR:
        g = gcd(SR, sr)
        y = resample_poly(y, SR // g, sr // g)
    return y, kiem_tra


def ma_bam_pcm(y):
    """Mã băm của tín hiệu sau khi đưa về mono 16 kHz, lượng tử 16 bit; dùng để nhận ra truy vấn trùng tệp trong kho."""
    pcm = np.clip(np.round(y * 32768), -32768, 32767).astype('<i2')
    return hashlib.sha256(pcm.tobytes()).hexdigest()


def tinh_dac_trung(y):
    """Bước 2-6: trả về (21 giá trị gốc bộ A, 39 giá trị gốc bộ B)."""
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
