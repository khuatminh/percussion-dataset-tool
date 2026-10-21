# Yêu cầu 3 và 4: CSDL đặc trưng và tìm kiếm âm tương đồng

Thư mục này cài đặt đúng những gì Mục 9–10 của báo cáo Yêu cầu 1–2 mô tả. Mục 10.3 "Sử dụng khi lưu trữ và tìm kiếm" là đặc tả chính.

- **Yêu cầu 3:** trích ba bộ đặc trưng A (21 chiều), B (39 chiều) và C (60 chiều) cho 655 tệp, rồi lưu vào một CSDL SQLite.
- **Yêu cầu 4:** nhận một tệp âm thanh nhạc cụ gõ mới và trả về 5 tệp giống nhất trong kho. Phần tìm kiếm dùng một cây k-d tự cài.

Hàm tính đặc trưng được dùng lại nguyên văn từ `bao_cao_bo_go/trich_xuat_dac_trung.py`. Vì vậy các giá trị trong CSDL khớp với `filtered_output/features/` đến sai số tương đối 1,5·10⁻¹¹.

## Cài đặt và chạy

Từ thư mục gốc repo, dùng Python 3.11 trở lên:

```sh
python3 -m venv .venv-audio
.venv-audio/bin/python -m pip install -r csdl_tim_kiem/requirements.txt
.venv-audio/bin/python csdl_tim_kiem/xay_dung_csdl.py          # tạo csdl_dac_trung.sqlite (~5 s)
.venv-audio/bin/python csdl_tim_kiem/tim_kiem.py tep_moi.wav    # tìm 5 tệp giống nhất, bộ C
.venv-audio/bin/python csdl_tim_kiem/tim_kiem.py tep_moi.wav --bo A --json
.venv-audio/bin/python csdl_tim_kiem/danh_gia.py                # đánh giá (~1,5 phút)
.venv-audio/bin/python -m pytest csdl_tim_kiem/kiem_thu.py
```

Trên Windows, thay `.venv-audio/bin/python` bằng `.venv-audio\Scripts\python.exe`. Tệp `csdl_dac_trung.sqlite` đã có sẵn trong repo, nên muốn tìm kiếm thì không cần chạy lại bước xây dựng.

## Các tệp

| Tệp | Nội dung |
|---|---|
| `dac_trung.py` | Đọc tệp truy vấn bất kỳ định dạng (WAV, FLAC, OGG, AIFF, MP3), đưa về mono 16 kHz, tính đặc trưng, chuẩn hóa và tạo u_A, u_B, u_C |
| `cay_kd.py` | Cây k-d tìm k láng giềng gần nhất, kèm hàm tìm vét cạn để kiểm chứng |
| `csdl.py` | Lược đồ SQLite, ghi CSDL, nạp CSDL, tìm kiếm và giải thích kết quả |
| `xay_dung_csdl.py` | Yêu cầu 3: kiểm tra mã băm, trích đặc trưng cho 655 tệp, ghi CSDL |
| `tim_kiem.py` | Yêu cầu 4: chương trình dòng lệnh để tìm top 5 |
| `danh_gia.py` | Đánh giá A, B, C, ghi kết quả vào `ket_qua_danh_gia/` |
| `kiem_thu.py` | Kiểm thử bằng pytest |

## Lược đồ CSDL

| Bảng | Một hàng là | Cột chính |
|---|---|---|
| `tep_am_thanh` | một tệp | `ma_tep` (khóa, trùng `sample_id` trong bảng đặc trưng), `duong_dan`, `nhan`, `nguon`, `ten_goc`, `nguoi_tai_len`, `nhom_ban_thu`, `thoi_luong_s`, `sha256`, `pcm16_sha256` |
| `dac_trung_goc` | một tệp | 21 cột bộ A rồi 39 cột bộ B, giá trị gốc chưa chuẩn hóa, theo đúng thứ tự Phụ lục |
| `tham_so_chuan_hoa` | một chiều | `bo` (A/B), `chieu`, `thuoc_tinh`, `mu`, `s`; tổng cộng 60 hàng |
| `vector_dac_trung` | một tệp × một bộ | `bo` (A/B/C), `so_chieu`, `vec` (BLOB float64 little-endian của u_A, u_B hoặc u_C) |
| `thong_tin` | một khóa | phiên bản dữ liệu, thời điểm tạo, số tệp, phiên bản thư viện |

Khi mở CSDL, chương trình nạp các vector vào bộ nhớ và dựng mỗi bộ một cây k-d. Với 655 tệp, việc này mất chưa đến 1 giây. Có thể truy vấn trực tiếp bằng SQL, ví dụ:

```sql
SELECT t.nhan, AVG(g.centroid_hz_mean) FROM tep_am_thanh t JOIN dac_trung_goc g USING (ma_tep) GROUP BY t.nhan;
```

## Quy trình tìm kiếm (Mục 10.3)

1. Đọc tệp truy vấn, trộn các kênh thành một kênh và đổi tần số lấy mẫu về 16 kHz bằng `resample_poly`.
2. Từ chối tệp ngắn hơn 0,1 s, tệp im lặng hoặc không có khối 10 ms nào có RMS > 0,01, và tệp không đọc được.
3. Tính 21 + 39 giá trị gốc theo bước 1–6, chuẩn hóa bằng μ_j, s_j **đã lưu** (không tính lại), rồi tạo u_A, u_B, u_C.
4. Nếu mã băm PCM của truy vấn trùng một tệp trong kho, bỏ chính tệp đó khỏi kết quả.
5. Tìm 5 tệp có khoảng cách Euclid d_S nhỏ nhất bằng cây k-d, sắp tăng dần. Độ tương đồng hiển thị là s = 1/(1+d).
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
  | Giảm âm lượng 20 dB | 0,99 | 0,97 | 0,99 |
  | Stereo 44,1 kHz | 0,99 | 1,00 | 1,00 |
  | MP3 44,1 kHz | 0,97 | 0,79 | 0,85 |
  | Thêm nhiễu trắng SNR 30 dB | 0,53 | 0,58 | 0,64 |

  Nhiễu nền lấp đầy phần đuôi im lặng và làm thay đổi độ phẳng, thời gian có tín hiệu và MFCC, nên cả ba bộ đều giảm mạnh. Đây là giới hạn đã biết của cách đặt ngưỡng RMS cố định.
- **Kiểm chứng cây k-d:** với cả 655 truy vấn và cả ba bộ, kết quả giống hệt tìm vét cạn. Trung bình cây k-d tính 358 khoảng cách cho bộ A, còn với B và C (39–60 chiều) thì gần như phải tính hết 640 khoảng cách. Đây là hiện tượng "lời nguyền số chiều" quen thuộc của cây k-d. Mỗi truy vấn mất khoảng 5 ms, phần lớn là thời gian tính đặc trưng.

**Bộ mặc định: C.** Mục 10.3 đề xuất A vì A có tỷ số Q cao nhất, đồng thời ghi rằng việc chọn bộ cuối cùng sẽ dựa trên đánh giá ở Yêu cầu 4. Trên cả hai cách đánh giá, C có P@5 và tỷ lệ đúng ở hạng 1 cao nhất, nên `tim_kiem.py` dùng C làm mặc định; có thể chọn bộ khác bằng `--bo A` hoặc `--bo B`. A vẫn bền hơn với MP3 và cho lời giải thích dễ hiểu hơn.
