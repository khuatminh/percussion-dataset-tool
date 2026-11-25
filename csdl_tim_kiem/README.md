# Yêu cầu 3, 4 và 5: CSDL đặc trưng, tìm kiếm âm tương đồng và demo

Thư mục này cài đặt đúng những gì Mục 9–10 của báo cáo Yêu cầu 1–2 mô tả. Mục 10.3 "Sử dụng khi lưu trữ và tìm kiếm" là đặc tả chính.

- **Yêu cầu 3:** trích ba bộ đặc trưng A (21 chiều), B (39 chiều) và C (60 chiều) cho 655 tệp, rồi lưu vào CSDL **PostgreSQL 17 + pgvector 0.8**, vector đặc trưng có kiểu `vector` và chỉ mục HNSW.
- **Yêu cầu 4:** nhận một tệp âm thanh nhạc cụ gõ mới và trả về 5 tệp giống nhất trong kho. Mặc định PostgreSQL tự tìm bằng truy vấn SQL `ORDER BY u <-> q LIMIT 5`; cây k-d tự cài và tìm vét cạn được giữ để đối chiếu.
- **Yêu cầu 5:** giao diện web cục bộ `giao_dien.py` (nghe truy vấn và từng kết quả, xem bảng kết quả trung gian).

Báo cáo Yêu cầu 1–4: [`../bao_cao_bo_go/bao_cao_mmdb.tex`](../bao_cao_bo_go/bao_cao_mmdb.tex) (Phần III–IV viết từ số liệu của thư mục này).

Hàm tính đặc trưng được dùng lại nguyên văn từ `bao_cao_bo_go/trich_xuat_dac_trung.py`. Vì vậy các giá trị trong CSDL khớp hoàn toàn với `filtered_output/features/` (sai số tương đối lớn nhất bằng 0).

## Cài đặt và chạy

Cần Docker (Docker Desktop) và Python 3.11 trở lên. Từ thư mục gốc repo:

```sh
docker compose up -d --wait                                     # PostgreSQL + pgvector ở localhost:5433
python3 -m venv .venv-audio
.venv-audio/bin/python -m pip install -r csdl_tim_kiem/requirements.txt
.venv-audio/bin/python csdl_tim_kiem/xay_dung_csdl.py          # tạo bảng và nạp 655 tệp (~3 s)
.venv-audio/bin/python csdl_tim_kiem/tim_kiem.py tep_moi.wav    # tìm 5 tệp giống nhất, bộ C
.venv-audio/bin/python csdl_tim_kiem/tim_kiem.py tep_moi.wav --bo A --json
.venv-audio/bin/python csdl_tim_kiem/tim_kiem.py tep_moi.wav --cach cay_kd   # hoặc vet_can
.venv-audio/bin/python csdl_tim_kiem/giao_dien.py              # Yêu cầu 5: mở http://127.0.0.1:8765
.venv-audio/bin/python csdl_tim_kiem/danh_gia.py                # đánh giá (~40 s)
.venv-audio/bin/python csdl_tim_kiem/minh_hoa.py                # kết quả trung gian + hình 3-6 của báo cáo
.venv-audio/bin/python -m pytest csdl_tim_kiem/kiem_thu.py csdl_tim_kiem/test_giao_dien.py
```

Môi trường đã chạy và kiểm thử: macOS (Apple Silicon) với Docker Desktop; các lệnh trên viết cho macOS/Linux. Dữ liệu PostgreSQL nằm trong volume Docker `du_lieu_pg`, vẫn còn sau khi tắt container (`docker compose down`); `docker compose down -v` xóa hẳn, khi đó chạy lại `xay_dung_csdl.py`. Đổi chuỗi kết nối bằng `--db` hoặc biến môi trường `CSDL_URL` (mặc định `postgresql://bogo:bogo@localhost:5433/csdl_bo_go`). Xem trực tiếp: `docker compose exec csdl psql -U bogo -d csdl_bo_go`.

## Các tệp

| Tệp | Nội dung |
|---|---|
| `dac_trung.py` | Đọc tệp truy vấn bất kỳ định dạng (WAV, FLAC, OGG, AIFF, MP3), đưa về mono 16 kHz, tính đặc trưng, chuẩn hóa và tạo u_A, u_B, u_C |
| `cay_kd.py` | Cây k-d tìm k láng giềng gần nhất, kèm hàm tìm vét cạn để kiểm chứng |
| `csdl.py` | Lược đồ PostgreSQL, ghi CSDL, nạp CSDL, tìm kiếm (pgvector / cây k-d / vét cạn) và giải thích kết quả |
| `../compose.yaml` | Dịch vụ PostgreSQL + pgvector chạy bằng Docker |
| `xay_dung_csdl.py` | Yêu cầu 3: kiểm tra mã băm, trích đặc trưng cho 655 tệp, ghi CSDL |
| `tim_kiem.py` | Yêu cầu 4: chương trình dòng lệnh để tìm top 5 |
| `giao_dien.py`, `web/` | Yêu cầu 5: giao diện web cục bộ (chỉ nhận yêu cầu từ 127.0.0.1) |
| `danh_gia.py` | Đánh giá A, B, C, ghi kết quả vào `ket_qua_danh_gia/` |
| `minh_hoa.py` | Yêu cầu 4b: ghi `ket_qua_danh_gia/minh_hoa.json` (giá trị trung gian của 3 truy vấn ví dụ) và vẽ hình 3–6 vào `bao_cao_bo_go/hinh/` |
| `truy_van_thu/` | 77 tệp truy vấn **không thuộc kho**, lấy từ Freesound One-Shot Percussive Sounds: `ngoai_kho/` 73 tệp của 12 nhạc cụ ngoài 13 lớp, `trong_lop/` 4 tệp mới của lớp đã có; `danh_sach.csv` ghi mã Freesound, tên gốc, kết quả kiểm tra Mục 2 và đối chiếu nhãn với 3 gợi ý của mô hình CLAP (38/73 tệp ngoài kho có nhãn trong top-3; nhãn **chưa được nghe kiểm tra**) |
| `chuan_bi_truy_van_thu.py` | Tạo lại `truy_van_thu/` từ bản tải Freesound (chỉ cần chạy một lần) |
| `kiem_thu.py`, `test_giao_dien.py` | Kiểm thử bằng pytest (17 phép) |

## Lược đồ CSDL

| Bảng | Một hàng là | Cột chính |
|---|---|---|
| `audio_files` | một tệp | Bảng danh mục (Mục 2.3): `file_id` (khóa, trùng `sample_id` trong bảng đặc trưng), `path`, `label`, `source`, `original_name`, `uploader`, `recording_group`, `sha256`, `pcm16_sha256` |
| `signal_checks` | một tệp | Bảng kiểm kê (Mục 2.3): `duration_s`, `active_duration_s`, `peak_dbfs`, `first_sample_ratio`, `tail_rms_ratio`, `clipping_ratio`; ràng buộc `CHECK` đúng các ngưỡng Mục 2, khớp `filtered_output/evidence/inventory.csv` |
| `raw_features` | một tệp | 21 cột bộ A rồi 39 cột bộ B, giá trị gốc chưa chuẩn hóa, theo đúng thứ tự Phụ lục |
| `normalization_params` | một chiều | `feature_set` (A/B), `dim`, `feature_name`, `mean`, `std`; tổng cộng 60 hàng |
| `feature_vectors` | một tệp | `u_a vector(21)`, `u_b vector(39)`, `u_c vector(60)`; mỗi cột một chỉ mục HNSW (`vector_l2_ops`) |
| `db_info` (`key`, `value`) | một khóa | phiên bản dữ liệu, thời điểm tạo, số tệp, phiên bản thư viện |

Các bảng có khóa ngoại tới `audio_files` và ràng buộc `CHECK`; `xay_dung_csdl.py` ghi toàn bộ trong một giao dịch. pgvector lưu số thực 32 bit, nên `feature_vectors` là bản phục vụ tìm kiếm; giá trị chính xác 64 bit nằm ở `raw_features` và `normalization_params`. Khi mở CSDL, chương trình dựng lại u_A, u_B, u_C 64 bit từ hai bảng này (u_C trùng `features_C_standardized.csv`, sai số 0) và dựng mỗi bộ một cây k-d (dưới 1 giây). PostgreSQL chọn 10 ứng viên gần nhất, khoảng cách của chúng được tính lại bằng số thực 64 bit theo Bảng 6 của báo cáo rồi lấy 5.

Có thể truy vấn trực tiếp bằng SQL, ví dụ:

```sql
SELECT t.label, AVG(g.centroid_hz_mean) FROM audio_files t JOIN raw_features g USING (file_id) GROUP BY t.label;
-- 5 tệp gần tệp số 1 nhất theo bộ C
SELECT t.file_id, t.label, v.u_c <-> q.u_c AS d
FROM feature_vectors v JOIN audio_files t USING (file_id), (SELECT u_c FROM feature_vectors WHERE file_id = 1) q
WHERE v.file_id <> 1 ORDER BY d LIMIT 5;
```

## Quy trình tìm kiếm (Mục 10.3)

1. Đọc tệp truy vấn, trộn các kênh thành một kênh và đổi tần số lấy mẫu về 16 kHz bằng `resample_poly`.
2. Áp dụng đủ điều kiện kiểm tra tín hiệu của Mục 2 lên tệp gốc (trước khi trộn kênh): đọc được, không rỗng, không có giá trị không xác định/vô hạn; dài ≥ 0,1 s và phần có tiếng ≥ 0,05 s; đỉnh ≥ −40 dBFS; mẫu đầu ≤ 10% biên độ lớn nhất; RMS 10 ms cuối ≤ 30% đỉnh; không quá 1% số mẫu có biên độ ≥ 0,999. Cùng hàm này kiểm tra 655 tệp khi xây dựng CSDL. Tệp không có khối 10 ms nào có RMS > 0,01 sau chuẩn hóa đỉnh cũng bị từ chối.
3. Tính 21 + 39 giá trị gốc theo bước 1–6, chuẩn hóa bằng μ_j, s_j **đã lưu** (không tính lại), rồi tạo u_A, u_B, u_C.
4. Nếu mã băm PCM của truy vấn trùng một tệp trong kho, bỏ chính tệp đó khỏi kết quả.
5. Tìm 5 tệp có khoảng cách Euclid d_S nhỏ nhất bằng truy vấn pgvector (hoặc cây k-d với `--cach cay_kd`), sắp tăng dần. Độ tương đồng hiển thị là s = 1/(1+d).
6. Với mỗi kết quả, in ra 3 thuộc tính bộ A giống nhất và 3 thuộc tính khác nhất, đo bằng |Δz|.

Chiều chia ở mỗi nút của cây k-d là chiều có độ trải lớn nhất trong nhánh, và điểm chia là trung vị. Nếu hai tệp có khoảng cách bằng nhau, tệp có mã nhỏ hơn đứng trước. Nhờ vậy, cây k-d và tìm vét cạn cho cùng một danh sách.

## Kết quả đánh giá

Chạy `danh_gia.py`; số liệu đầy đủ nằm trong `ket_qua_danh_gia/tong_hop.json` và `theo_lop.csv`. P@5 là tỷ lệ tệp cùng nhãn với truy vấn trong 5 kết quả. Cột "TB lớp" lấy trung bình 13 lớp với trọng số như nhau, để kick và snare không lấn át.

| Phép đánh giá | Bộ | P@5 mọi truy vấn | P@5 TB lớp | Đúng ở hạng 1 |
|---|---|---|---|---|
| Bỏ-một-ra, 655 truy vấn | A | 0,799 | 0,674 | 0,863 |
| | B | 0,730 | 0,622 | 0,815 |
| | **C** | **0,832** | **0,741** | **0,896** |
| Chia theo nhóm bản thu, 639 truy vấn | A | 0,621 | 0,446 | 0,684 |
| | B | 0,571 | 0,424 | 0,649 |
| | **C** | **0,666** | **0,521** | **0,728** |

- **Chia theo nhóm bản thu:** dữ liệu được chia 5 phần, mỗi phần 131 tệp. Tệp cùng người tải lên (Freesound), cùng bộ trống (IDMT) hoặc cùng cách đánh và độ to (Iowa) luôn nằm chung một phần, tổng cộng 136 nhóm. μ, s chỉ tính trên 4 phần xây dựng. Toàn bộ 16 tệp agogo đến từ một người tải lên, nên agogo không thể vừa nằm trong kho vừa làm truy vấn và bị bỏ khỏi phép đánh giá này. Phép đánh giá này gần với truy vấn "tệp mới thật" hơn bỏ-một-ra, nên điểm thấp hơn là điều dự kiến.
- **Lớp khó:** conga, vibraphone và xylophone có P@5 dưới 0,5 ở cả hai cách đánh giá. Chúng thường bị nhầm với tom và marimba, đúng như các nhóm dễ nhầm lẫn mà báo cáo đã nêu.
- **Độ bền** (truy vấn là bản biến đổi của chính tệp trong kho, tỷ lệ tìm lại bản gốc ở hạng 1 với A / B / C):

  | Biến đổi | A | B | C |
  |---|---|---|---|
  | Giảm âm lượng 20 dB (624 truy vấn) | 1,00 | 0,97 | 0,99 |
  | Stereo 44,1 kHz | 0,99 | 1,00 | 1,00 |
  | MP3 44,1 kHz | 0,97 | 0,79 | 0,85 |
  | Thêm nhiễu trắng SNR 30 dB (654 truy vấn) | 0,53 | 0,58 | 0,64 |

  Nhiễu nền lấp đầy phần đuôi im lặng và làm thay đổi độ phẳng, thời gian có tín hiệu và MFCC, nên cả ba bộ đều giảm mạnh. Đây là giới hạn đã biết của cách đặt ngưỡng RMS cố định. Điều kiện Mục 2 từ chối 31 bản giảm 20 dB (tệp gốc có đỉnh dưới −20 dBFS nên bản giảm có đỉnh dưới −40 dBFS) và 1 bản thêm nhiễu (mẫu đầu lớn hơn 10% đỉnh); tỷ lệ tính trên các truy vấn còn lại.
- **Kiểm chứng cây k-d:** với cả 655 truy vấn và cả ba bộ, kết quả giống hệt tìm vét cạn. Trung bình cây k-d tính 358 khoảng cách cho bộ A, còn với B và C (39–60 chiều) thì gần như phải tính hết 640 khoảng cách. Đây là hiện tượng "lời nguyền số chiều" quen thuộc của cây k-d.
- **Kiểm chứng pgvector:** truy vấn SQL trong PostgreSQL cho cùng 5 tệp, cùng thứ tự và cùng khoảng cách với tìm vét cạn ở cả 655 truy vấn và cả ba bộ. Với 655 hàng, trình tối ưu của PostgreSQL chọn quét tuần tự (chính xác, khoảng 0,2 ms) vì rẻ hơn dùng chỉ mục HNSW; chỉ mục sẽ được dùng khi kho lớn hơn. Khi bắt buộc dùng chỉ mục HNSW (tìm xấp xỉ), 5 kết quả trùng vét cạn ở 100% / 99,91% / 99,85% vị trí (A / B / C). Trung vị trên 100 truy vấn: đọc + kiểm tra + trích đặc trưng ~1 ms; tìm top-5 bộ C ~1–2 ms qua PostgreSQL, ~1,2 ms cây k-d, ~0,1 ms vét cạn NumPy.
- **Nhạc cụ ngoài kho** (`truy_van_thu/ngoai_kho/`, 73 tệp, 12 nhạc cụ): 4 tệp dưới 0,1 s bị từ chối, 69 tệp đều nhận đủ 5 kết quả. Với bộ C, djembe/bongo/tabla nhận chủ yếu tom, conga, kick (cùng họ màng rung 92–100%); triangle nhận cymbal, hi-hat; nhạc cụ gỗ (castanets, woodblock, cajon) ít khi nhận kết quả cùng họ vì kho chỉ có claves. Đây là mô tả hành vi, không phải độ chính xác (không có đáp án đúng).

**Bộ mặc định: C.** Mục 10.3 đề xuất A vì A có tỷ số Q cao nhất, đồng thời ghi rằng việc chọn bộ cuối cùng sẽ dựa trên đánh giá ở Yêu cầu 4. Trên cả hai cách đánh giá, C có P@5 và tỷ lệ đúng ở hạng 1 cao nhất, nên `tim_kiem.py` dùng C làm mặc định; có thể chọn bộ khác bằng `--bo A` hoặc `--bo B`. A vẫn bền hơn với MP3 và cho lời giải thích dễ hiểu hơn.
