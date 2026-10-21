"""CSDL SQLite quản lý đặc trưng âm thanh và tìm kiếm 5 tệp tương đồng nhất (Yêu cầu 3-4).

Lược đồ theo Mục 10.3 của báo cáo:
  tep_am_thanh   một hàng cho mỗi tệp: mã, nhãn, đường dẫn, nguồn, thời lượng, mã băm
  dac_trung_goc  giá trị gốc (chưa chuẩn hóa) của 21 thuộc tính A và 39 thuộc tính B, đúng thứ tự Phụ lục
  tham_so_chuan_hoa  60 cặp μ_j, s_j, tính một lần trên cả kho
  vector_dac_trung   u_A, u_B, u_C lưu sẵn (BLOB float64) để tìm nhanh
  thong_tin      phiên bản, thời điểm tạo, số tệp
"""
import sqlite3
from pathlib import Path

import numpy as np

from cay_kd import CayKD, tim_tuan_tu
from dac_trung import (A_NAMES, B_NAMES, DIM, TEN_A, TEN_B, doc_am_thanh, ma_bam_pcm,
                       tham_so_chuan_hoa, tinh_dac_trung, vector_u)

DB_MAC_DINH = Path(__file__).resolve().parent / 'csdl_dac_trung.sqlite'
BO_MAC_DINH = 'C'  # Mục 10.3 đề xuất A, nhưng đánh giá ở danh_gia.py cho C có P@5 cao nhất

LUOC_DO = f"""
CREATE TABLE thong_tin (khoa TEXT PRIMARY KEY, gia_tri TEXT NOT NULL);
CREATE TABLE tep_am_thanh (
    ma_tep        INTEGER PRIMARY KEY,
    duong_dan     TEXT NOT NULL UNIQUE,   -- tính từ thư mục filtered_output/
    nhan          TEXT NOT NULL,
    nguon         TEXT NOT NULL,          -- Freesound / IDMT / Iowa
    ten_goc       TEXT,
    nguoi_tai_len TEXT,
    nhom_ban_thu  TEXT NOT NULL,          -- dùng để chia tập khi đánh giá
    thoi_luong_s  REAL NOT NULL,
    sha256        TEXT NOT NULL,
    pcm16_sha256  TEXT NOT NULL
);
CREATE INDEX idx_tep_nhan ON tep_am_thanh(nhan);
CREATE INDEX idx_tep_pcm ON tep_am_thanh(pcm16_sha256);
CREATE TABLE dac_trung_goc (
    ma_tep INTEGER PRIMARY KEY REFERENCES tep_am_thanh(ma_tep),
    {', '.join(f'{n} REAL NOT NULL' for n in A_NAMES + B_NAMES)}
);
CREATE TABLE tham_so_chuan_hoa (
    bo TEXT NOT NULL CHECK (bo IN ('A','B')),
    chieu INTEGER NOT NULL,
    thuoc_tinh TEXT NOT NULL,
    mu REAL NOT NULL,
    s REAL NOT NULL,
    PRIMARY KEY (bo, chieu)
);
CREATE TABLE vector_dac_trung (
    ma_tep INTEGER NOT NULL REFERENCES tep_am_thanh(ma_tep),
    bo TEXT NOT NULL CHECK (bo IN ('A','B','C')),
    so_chieu INTEGER NOT NULL,
    vec BLOB NOT NULL,
    PRIMARY KEY (ma_tep, bo)
);
"""


def ghi_csdl(duong_dan_db, tep, A, B, thong_tin):
    """Tạo mới CSDL từ danh sách tệp (dict) và hai ma trận đặc trưng gốc A (n×21), B (n×39)."""
    duong_dan_db = Path(duong_dan_db)
    if duong_dan_db.exists():
        duong_dan_db.unlink()
    mu_a, s_a = tham_so_chuan_hoa(A)
    mu_b, s_b = tham_so_chuan_hoa(B)
    U = vector_u(A, B, mu_a, s_a, mu_b, s_b)
    con = sqlite3.connect(duong_dan_db)
    with con:
        con.executescript(LUOC_DO)
        con.executemany('INSERT INTO thong_tin VALUES (?,?)', [(k, str(v)) for k, v in thong_tin.items()])
        cot = ['ma_tep', 'duong_dan', 'nhan', 'nguon', 'ten_goc', 'nguoi_tai_len', 'nhom_ban_thu',
               'thoi_luong_s', 'sha256', 'pcm16_sha256']
        con.executemany(f'INSERT INTO tep_am_thanh VALUES ({",".join("?" * len(cot))})',
                        [tuple(t[c] for c in cot) for t in tep])
        con.executemany(f'INSERT INTO dac_trung_goc VALUES ({",".join("?" * 61)})',
                        [(t['ma_tep'], *map(float, a), *map(float, b)) for t, a, b in zip(tep, A, B)])
        con.executemany('INSERT INTO tham_so_chuan_hoa VALUES (?,?,?,?,?)',
                        [('A', j + 1, n, float(mu_a[j]), float(s_a[j])) for j, n in enumerate(A_NAMES)]
                        + [('B', j + 1, n, float(mu_b[j]), float(s_b[j])) for j, n in enumerate(B_NAMES)])
        con.executemany('INSERT INTO vector_dac_trung VALUES (?,?,?,?)',
                        [(t['ma_tep'], bo, DIM[bo], U[bo][i].astype('<f8').tobytes())
                         for bo in 'ABC' for i, t in enumerate(tep)])
    con.close()


class CSDL:
    """Mở CSDL, nạp vector vào bộ nhớ và dựng một cây k-d cho mỗi bộ đặc trưng."""

    def __init__(self, duong_dan_db=DB_MAC_DINH):
        if not Path(duong_dan_db).exists():
            raise FileNotFoundError(f'Chưa có CSDL {duong_dan_db}; chạy xay_dung_csdl.py trước.')
        self.con = sqlite3.connect(duong_dan_db)
        self.con.row_factory = sqlite3.Row
        self.tep = {r['ma_tep']: dict(r) for r in self.con.execute('SELECT * FROM tep_am_thanh ORDER BY ma_tep')}
        self.ma = np.array(list(self.tep))
        tham_so = self.con.execute('SELECT bo, mu, s FROM tham_so_chuan_hoa ORDER BY bo, chieu').fetchall()
        self.mu = {bo: np.array([r['mu'] for r in tham_so if r['bo'] == bo]) for bo in 'AB'}
        self.s = {bo: np.array([r['s'] for r in tham_so if r['bo'] == bo]) for bo in 'AB'}
        self.U, self.cay = {}, {}
        for bo in 'ABC':
            hang = self.con.execute('SELECT ma_tep, vec FROM vector_dac_trung WHERE bo=? ORDER BY ma_tep', (bo,))
            ma, vec = zip(*[(r['ma_tep'], np.frombuffer(r['vec'], '<f8')) for r in hang])
            assert list(ma) == list(self.ma)
            self.U[bo] = np.vstack(vec)
            self.cay[bo] = CayKD(self.U[bo], self.ma)
        goc = self.con.execute(f'SELECT {", ".join(A_NAMES + B_NAMES)} FROM dac_trung_goc ORDER BY ma_tep').fetchall()
        self.goc = np.array(goc, dtype=np.float64)

    def vector_truy_van(self, duong_dan):
        """Bước xử lý truy vấn ở Mục 10.3: mono 16 kHz, bước 1-6, chuẩn hóa bằng μ, s đã lưu."""
        y = doc_am_thanh(duong_dan)
        a, b = tinh_dac_trung(y)
        u = vector_u(a, b, self.mu['A'], self.s['A'], self.mu['B'], self.s['B'])
        return dict(u=u, a=a, b=b, pcm16_sha256=ma_bam_pcm(y), thoi_luong_s=len(y) / 16000)

    def tim_kiem(self, duong_dan, bo=BO_MAC_DINH, k=5, vet_can=False):
        """Trả về thông tin truy vấn và k tệp gần nhất theo d_bo, tăng dần (độ tương đồng s=1/(1+d) giảm dần)."""
        tv = self.vector_truy_van(duong_dan)
        trung = [r[0] for r in self.con.execute('SELECT ma_tep FROM tep_am_thanh WHERE pcm16_sha256=?',
                                                (tv['pcm16_sha256'],))]
        q = tv['u'][bo]
        if vet_can:
            kq = tim_tuan_tu(self.U[bo], self.ma, q, k, trung)
        else:
            kq = self.cay[bo].tim(q, k, trung)
        tv['bo'], tv['trung_tep_trong_kho'] = bo, trung
        tv['so_phep_tinh_khoang_cach'] = len(self.ma) - len(trung) if vet_can else self.cay[bo].so_phep_tinh
        tv['ket_qua'] = [dict(self.tep[m], hang=i + 1, khoang_cach=d, do_tuong_dong=1 / (1 + d),
                              giai_thich=self.giai_thich(tv, m))
                         for i, (d, m) in enumerate(kq)]
        return tv

    def giai_thich(self, tv, ma_tep, so_luong=3):
        """Các thuộc tính bộ A giống nhất và khác nhất giữa truy vấn và một tệp (theo |Δz|)."""
        i = int(np.searchsorted(self.ma, ma_tep))
        dz = np.abs((tv['a'] - self.goc[i, :21]) / self.s['A'])
        thu_tu = np.argsort(dz, kind='stable')
        return dict(giong=[(TEN_A[j], float(dz[j])) for j in thu_tu[:so_luong]],
                    khac=[(TEN_A[j], float(dz[j])) for j in thu_tu[::-1][:so_luong]])


__all__ = ['CSDL', 'ghi_csdl', 'DB_MAC_DINH', 'BO_MAC_DINH', 'TEN_B']
