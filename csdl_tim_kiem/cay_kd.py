"""Cây k-d (Bài giảng 6) để tìm k láng giềng gần nhất theo khoảng cách Euclid.

Mỗi nút giữ một điểm. Ở mỗi nút, chiều chia là chiều có độ trải (max - min) lớn nhất
trong các điểm của nhánh đó, và điểm chia là điểm trung vị theo chiều này. Khi tìm kiếm,
nhánh bên kia chỉ được xét nếu siêu phẳng chia còn gần hơn láng giềng xa nhất đang giữ.
Kết quả giống hệt tìm tuần tự (có kiểm chứng trong danh_gia.py và kiem_thu.py).
"""
import heapq

import numpy as np


class _Nut:
    __slots__ = ('chi_so', 'chieu', 'trai', 'phai')

    def __init__(self, chi_so, chieu, trai, phai):
        self.chi_so, self.chieu, self.trai, self.phai = chi_so, chieu, trai, phai


class CayKD:
    def __init__(self, X, ma=None):
        self.X = np.asarray(X, dtype=np.float64)
        self.ma = np.arange(len(self.X)) if ma is None else np.asarray(ma)
        self.goc = self._xay(np.arange(len(self.X)))
        self.so_phep_tinh = 0  # số lần tính khoảng cách ở lần tìm gần nhất

    def _xay(self, cs):
        if len(cs) == 0:
            return None
        P = self.X[cs]
        chieu = int(np.argmax(P.max(axis=0) - P.min(axis=0)))
        thu_tu = cs[np.argsort(P[:, chieu], kind='stable')]
        giua = len(thu_tu) // 2
        return _Nut(int(thu_tu[giua]), chieu, self._xay(thu_tu[:giua]), self._xay(thu_tu[giua + 1:]))

    def tim(self, q, k=5, bo_qua=()):
        """Trả về danh sách (khoảng cách, mã) của k điểm gần q nhất, tăng dần; bỏ các mã trong bo_qua."""
        q = np.asarray(q, dtype=np.float64)
        bo_qua = set(bo_qua)
        heap = []  # max-heap theo (-d², -mã): phần tử đầu là láng giềng "tệ" nhất đang giữ
        self.so_phep_tinh = 0

        def tham(nut):
            if nut is None:
                return
            i = nut.chi_so
            if self.ma[i] not in bo_qua:
                self.so_phep_tinh += 1
                d2 = float(np.sum((self.X[i] - q) ** 2))
                muc = (-d2, -int(self.ma[i]))
                if len(heap) < k:
                    heapq.heappush(heap, muc)
                elif muc > heap[0]:  # gần hơn, hoặc bằng khoảng cách nhưng mã nhỏ hơn
                    heapq.heapreplace(heap, muc)
            lech = q[nut.chieu] - self.X[i, nut.chieu]
            gan, xa = (nut.trai, nut.phai) if lech < 0 else (nut.phai, nut.trai)
            tham(gan)
            if len(heap) < k or lech * lech <= -heap[0][0]:
                tham(xa)

        tham(self.goc)
        return sorted((np.sqrt(-d2), -m) for d2, m in heap)


def tim_tuan_tu(X, ma, q, k=5, bo_qua=()):
    """Tìm vét cạn: cùng thứ tự (khoảng cách, mã) như CayKD.tim, dùng để kiểm chứng."""
    d2 = np.sum((np.asarray(X) - q) ** 2, axis=1)
    giu = ~np.isin(ma, list(bo_qua))
    thu_tu = np.lexsort((np.asarray(ma)[giu], d2[giu]))[:k]
    return [(float(np.sqrt(d2[giu][j])), int(np.asarray(ma)[giu][j])) for j in thu_tu]
