"""CSDL PostgreSQL + pgvector quản lý đặc trưng âm thanh và tìm 5 tệp tương đồng nhất (Yêu cầu 3-4).

Lược đồ theo Mục 10.3 của báo cáo:
  audio_files           bảng danh mục (Mục 2.3): mã, đường dẫn, nhãn, nguồn, người tải lên, mã băm
  signal_checks         bảng kiểm kê (Mục 2.3): thời lượng và số đo kiểm tra tín hiệu; CHECK đúng ngưỡng Mục 2
  raw_features          giá trị gốc (chưa chuẩn hóa) của 21 thuộc tính A và 39 thuộc tính B, đúng thứ tự Phụ lục
  normalization_params  60 cặp μ_j, s_j, tính một lần trên cả kho
  feature_vectors       u_A, u_B, u_C kiểu vector(21/39/60) của pgvector, mỗi cột một chỉ mục HNSW
  db_info               phiên bản, thời điểm tạo, số tệp

Ba cách tìm top k: 'pgvector' (truy vấn SQL `ORDER BY u <-> q`, do hệ CSDL thực hiện), 'cay_kd' (cây k-d tự
cài trong bộ nhớ) và 'vet_can' (so với mọi tệp, dùng để kiểm chứng). pgvector lưu số thực 32 bit, nên mọi khoảng
cách trả về đều được tính lại bằng số thực 64 bit (Bảng 6) từ u dựng lại theo giá trị gốc 64 bit và μ, s đã lưu.
"""
import os

import numpy as np
import psycopg
from psycopg.rows import dict_row

from cay_kd import CayKD, tim_tuan_tu
from dac_trung import (A_NAMES, B_NAMES, DIM, TEN_A, TEN_B, doc_am_thanh, ma_bam_pcm,
                       tham_so_chuan_hoa, tinh_dac_trung, vector_u)

URL_MAC_DINH = os.environ.get('CSDL_URL', 'postgresql://bogo:bogo@localhost:5433/csdl_bo_go')
BO_MAC_DINH = 'C'  # Mục 10.3 đề xuất A, nhưng đánh giá ở danh_gia.py cho C có P@5 cao nhất
CACH_TIM = ('pgvector', 'cay_kd', 'vet_can')

LUOC_DO = f"""
CREATE EXTENSION IF NOT EXISTS vector;
DROP TABLE IF EXISTS feature_vectors, normalization_params, raw_features, signal_checks, audio_files, db_info;
CREATE TABLE db_info (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE audio_files (
    file_id         INTEGER PRIMARY KEY,
    path            TEXT NOT NULL UNIQUE,   -- tính từ thư mục filtered_output/
    label           TEXT NOT NULL,
    source          TEXT NOT NULL CHECK (source IN ('Freesound', 'IDMT', 'Iowa')),
    original_name   TEXT,
    uploader        TEXT,
    recording_group TEXT NOT NULL,          -- dùng để chia tập khi đánh giá
    sha256          CHAR(64) NOT NULL,
    pcm16_sha256    CHAR(64) NOT NULL
);
CREATE INDEX idx_audio_label ON audio_files(label);
CREATE INDEX idx_audio_pcm ON audio_files(pcm16_sha256);
CREATE TABLE signal_checks (
    file_id            INTEGER PRIMARY KEY REFERENCES audio_files(file_id) ON DELETE CASCADE,
    duration_s         DOUBLE PRECISION NOT NULL CHECK (duration_s >= 0.1),
    active_duration_s  DOUBLE PRECISION NOT NULL CHECK (active_duration_s >= 0.05),
    peak_dbfs          DOUBLE PRECISION NOT NULL CHECK (peak_dbfs >= -40),
    first_sample_ratio DOUBLE PRECISION NOT NULL CHECK (first_sample_ratio <= 0.1),
    tail_rms_ratio     DOUBLE PRECISION NOT NULL CHECK (tail_rms_ratio <= 0.3),
    clipping_ratio     DOUBLE PRECISION NOT NULL CHECK (clipping_ratio <= 0.01)
);
CREATE TABLE raw_features (
    file_id INTEGER PRIMARY KEY REFERENCES audio_files(file_id) ON DELETE CASCADE,
    {', '.join(f'{n} DOUBLE PRECISION NOT NULL' for n in A_NAMES + B_NAMES)}
);
CREATE TABLE normalization_params (
    feature_set  CHAR(1) NOT NULL CHECK (feature_set IN ('A','B')),
    dim          INTEGER NOT NULL,
    feature_name TEXT NOT NULL,
    mean         DOUBLE PRECISION NOT NULL,
    std          DOUBLE PRECISION NOT NULL CHECK (std > 0),
    PRIMARY KEY (feature_set, dim)
);
CREATE TABLE feature_vectors (
    file_id INTEGER PRIMARY KEY REFERENCES audio_files(file_id) ON DELETE CASCADE,
    u_a vector(21) NOT NULL,
    u_b vector(39) NOT NULL,
    u_c vector(60) NOT NULL
);
"""
# Tên cột trong CSDL (tiếng Anh) ứng với khóa dict dùng trong chương trình.
COT_TEP = dict(ma_tep='file_id', duong_dan='path', nhan='label', nguon='source', ten_goc='original_name',
               nguoi_tai_len='uploader', nhom_ban_thu='recording_group', sha256='sha256', pcm16_sha256='pcm16_sha256')
COT_KIEM_KE = dict(thoi_luong_s='duration_s', thoi_gian_co_tieng_s='active_duration_s', dinh_dbfs='peak_dbfs',
                   mau_dau_tuong_doi='first_sample_ratio', cuoi_tuong_doi='tail_rms_ratio',
                   ty_le_cat_dinh='clipping_ratio')
CHI_MUC = ''.join(f'CREATE INDEX idx_hnsw_{c} ON feature_vectors USING hnsw ({c} vector_l2_ops);'
                  for c in ('u_a', 'u_b', 'u_c'))


def _vec(v):
    """Chuỗi dạng '[x1,x2,...]' mà pgvector nhận làm giá trị vector."""
    return '[' + ','.join(map(str, np.asarray(v, dtype=np.float64).tolist())) + ']'


def ghi_csdl(url, tep, A, B, thong_tin):
    """Tạo lại toàn bộ bảng từ danh sách tệp (dict) và hai ma trận đặc trưng gốc A (n×21), B (n×39)."""
    mu_a, s_a = tham_so_chuan_hoa(A)
    mu_b, s_b = tham_so_chuan_hoa(B)
    U = vector_u(A, B, mu_a, s_a, mu_b, s_b)
    with psycopg.connect(url) as con, con.cursor() as cur:  # một giao dịch: lỗi giữa chừng thì không ghi gì
        cur.execute(LUOC_DO)
        cur.executemany('INSERT INTO db_info VALUES (%s,%s)', [(k, str(v)) for k, v in thong_tin.items()])
        cur.executemany(f'INSERT INTO audio_files ({",".join(COT_TEP.values())}) VALUES ({",".join(["%s"] * len(COT_TEP))})',
                        [tuple(t[c] for c in COT_TEP) for t in tep])
        cur.executemany(f'INSERT INTO signal_checks (file_id,{",".join(COT_KIEM_KE.values())}) VALUES ({",".join(["%s"] * 7)})',
                        [(t['ma_tep'], *(t['kiem_ke'][c] for c in COT_KIEM_KE)) for t in tep])
        cur.executemany(f'INSERT INTO raw_features VALUES ({",".join(["%s"] * 61)})',
                        [(t['ma_tep'], *map(float, a), *map(float, b)) for t, a, b in zip(tep, A, B)])
        cur.executemany('INSERT INTO normalization_params VALUES (%s,%s,%s,%s,%s)',
                        [('A', j + 1, n, float(mu_a[j]), float(s_a[j])) for j, n in enumerate(A_NAMES)]
                        + [('B', j + 1, n, float(mu_b[j]), float(s_b[j])) for j, n in enumerate(B_NAMES)])
        cur.executemany('INSERT INTO feature_vectors VALUES (%s,%s::vector,%s::vector,%s::vector)',
                        [(t['ma_tep'], _vec(U['A'][i]), _vec(U['B'][i]), _vec(U['C'][i]))
                         for i, t in enumerate(tep)])
        cur.execute(CHI_MUC)
        cur.execute('ANALYZE')
        cur.execute('SELECT pg_size_pretty(pg_database_size(current_database()))')
        return cur.fetchone()[0]


class CSDL:
    """Kết nối CSDL, nạp giá trị gốc vào bộ nhớ và dựng một cây k-d cho mỗi bộ đặc trưng."""

    def __init__(self, url=URL_MAC_DINH):
        try:
            self.con = psycopg.connect(url, row_factory=dict_row, autocommit=True)
            self.tep = {r['ma_tep']: r for r in self.con.execute(
                f'SELECT {", ".join(f"t.{c} AS {k}" for k, c in COT_TEP.items())}, k.duration_s AS thoi_luong_s '
                'FROM audio_files t JOIN signal_checks k USING (file_id) ORDER BY file_id')}
        except psycopg.OperationalError as e:
            raise ConnectionError(f'Không kết nối được {url}. Chạy `docker compose up -d` ở thư mục gốc repo.') from e
        except psycopg.errors.UndefinedTable as e:
            raise ConnectionError('CSDL chưa có bảng; chạy csdl_tim_kiem/xay_dung_csdl.py trước.') from e
        self.ma = np.array(list(self.tep))
        tham_so = self.con.execute('SELECT feature_set AS bo, mean AS mu, std AS s FROM normalization_params ORDER BY feature_set, dim').fetchall()
        self.mu = {bo: np.array([r['mu'] for r in tham_so if r['bo'] == bo]) for bo in 'AB'}
        self.s = {bo: np.array([r['s'] for r in tham_so if r['bo'] == bo]) for bo in 'AB'}
        goc = self.con.execute(f'SELECT {", ".join(A_NAMES + B_NAMES)} FROM raw_features ORDER BY file_id')
        self.goc = np.array([list(r.values()) for r in goc], dtype=np.float64)
        assert len(self.goc) == len(self.ma)
        self.U = vector_u(self.goc[:, :21], self.goc[:, 21:], self.mu['A'], self.s['A'], self.mu['B'], self.s['B'])
        self.cay = {bo: CayKD(self.U[bo], self.ma) for bo in 'ABC'}

    def vector_truy_van(self, duong_dan):
        """Bước xử lý truy vấn ở Mục 10.3: mono 16 kHz, bước 1-6, chuẩn hóa bằng μ, s đã lưu."""
        y, kiem_tra = doc_am_thanh(duong_dan)
        a, b = tinh_dac_trung(y)
        u = vector_u(a, b, self.mu['A'], self.s['A'], self.mu['B'], self.s['B'])
        return dict(u=u, a=a, b=b, pcm16_sha256=ma_bam_pcm(y), thoi_luong_s=kiem_tra['thoi_luong_s'],
                    kiem_tra_tin_hieu=kiem_tra)

    def tim_sql(self, q, bo, k, loai_tru=()):
        """k tệp gần nhất do PostgreSQL tìm bằng toán tử khoảng cách Euclid `<->` (dùng chỉ mục HNSW nếu có lợi).

        PostgreSQL trả về 2k ứng viên theo khoảng cách 32 bit; khoảng cách của các ứng viên được tính lại bằng số
        thực 64 bit rồi sắp (d, mã tệp) tăng dần, nên kết quả trùng tìm vét cạn cả khi hai tệp gần như cách đều.
        """
        cot = 'u_' + {'A': 'a', 'B': 'b', 'C': 'c'}[bo]
        hang = self.con.execute(f'SELECT file_id FROM feature_vectors WHERE file_id <> ALL(%(bo)s) '
                                f'ORDER BY {cot} <-> %(q)s::vector LIMIT %(k)s',
                                dict(q=_vec(q), bo=list(map(int, loai_tru)), k=2 * k))
        ung_vien = [r['file_id'] for r in hang]
        d = np.linalg.norm(self.U[bo][np.searchsorted(self.ma, ung_vien)] - q, axis=1)
        return sorted(zip(d.tolist(), ung_vien))[:k]

    def tim_kiem(self, duong_dan, bo=BO_MAC_DINH, k=5, cach='pgvector'):
        """Trả về thông tin truy vấn và k tệp gần nhất theo d_bo, tăng dần (độ tương đồng s=1/(1+d) giảm dần)."""
        if cach not in CACH_TIM:
            raise ValueError(f'cach phải là một trong {CACH_TIM}')
        tv = self.vector_truy_van(duong_dan)
        trung = [r['file_id'] for r in self.con.execute('SELECT file_id FROM audio_files WHERE pcm16_sha256=%s',
                                                       (tv['pcm16_sha256'],))]
        q = tv['u'][bo]
        if cach == 'pgvector':
            kq, so_phep = self.tim_sql(q, bo, k, trung), None
        elif cach == 'vet_can':
            kq, so_phep = tim_tuan_tu(self.U[bo], self.ma, q, k, trung), len(self.ma) - len(trung)
        else:
            kq = self.cay[bo].tim(q, k, trung)
            so_phep = self.cay[bo].so_phep_tinh
        tv['bo'], tv['cach'], tv['trung_tep_trong_kho'], tv['so_phep_tinh_khoang_cach'] = bo, cach, trung, so_phep
        tv['ket_qua'] = [dict(self.tep[m], hang=i + 1, khoang_cach=d, do_tuong_dong=1 / (1 + d),
                              khoang_cach_theo_bo=self.khoang_cach_theo_bo(tv, m),
                              giai_thich=self.giai_thich(tv, m))
                         for i, (d, m) in enumerate(kq)]
        tv['trung_gian'] = self.trung_gian(tv)
        return tv

    def khoang_cach_theo_bo(self, tv, ma_tep):
        """d_A, d_B, d_C giữa truy vấn và một tệp; dùng để minh họa d_C² = ½d_A² + ½d_B² (Mục 10.2)."""
        i = int(np.searchsorted(self.ma, ma_tep))
        return {bo: float(np.linalg.norm(tv['u'][bo] - self.U[bo][i])) for bo in 'ABC'}

    def trung_gian(self, tv):
        """Kết quả trung gian của truy vấn: 60 giá trị gốc x, tham số μ, s đã lưu và giá trị chuẩn hóa z."""
        x = np.concatenate([tv['a'], tv['b']])
        mu = np.concatenate([self.mu['A'], self.mu['B']])
        s = np.concatenate([self.s['A'], self.s['B']])
        chieu = [f'A{j + 1}' for j in range(21)] + [f'B{j + 1}' for j in range(39)]
        return [dict(chieu=c, ten=t, x=float(xj), mu=float(m), s=float(sj), z=float((xj - m) / sj))
                for c, t, xj, m, sj in zip(chieu, TEN_A + TEN_B, x, mu, s)]

    def giai_thich(self, tv, ma_tep, so_luong=3):
        """Các thuộc tính bộ A giống nhất và khác nhất giữa truy vấn và một tệp (theo |Δz|)."""
        i = int(np.searchsorted(self.ma, ma_tep))
        dz = np.abs((tv['a'] - self.goc[i, :21]) / self.s['A'])
        thu_tu = np.argsort(dz, kind='stable')
        return dict(giong=[(TEN_A[j], float(dz[j])) for j in thu_tu[:so_luong]],
                    khac=[(TEN_A[j], float(dz[j])) for j in thu_tu[::-1][:so_luong]])


__all__ = ['CSDL', 'ghi_csdl', 'URL_MAC_DINH', 'BO_MAC_DINH', 'CACH_TIM', 'TEN_B', 'DIM']
