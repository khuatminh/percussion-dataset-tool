# Báo cáo yêu cầu 1 và 2 — phiên bản 655 tệp

Bản hiện hành gồm **18 trang**, cập nhật ngày 20/10/2026, dùng **655 tệp / 13 nhóm nhạc cụ** trong `../filtered_output/accepted/`.

## Chỉnh sửa và biên dịch

- Sửa trực tiếp [`bao_cao_mmdb_yeu_cau_1_2.tex`](bao_cao_mmdb_yeu_cau_1_2.tex). Đây là nguồn chính, độc lập; các bảng đã được nhúng, không cần ảnh, bảng CSV hay file LaTeX phụ để biên dịch.
- [`bao_cao_mmdb_yeu_cau_1_2.pdf`](bao_cao_mmdb_yeu_cau_1_2.pdf) là bản PDF tương ứng khi bàn giao. Khi sửa nội dung, biên dịch và cập nhật PDF nếu muốn đồng bộ bản xem trước trong repo.
- Điền `HoTen`, `MSSV`, `Lop` ở đầu nguồn.
- Dùng XeLaTeX hoặc Tectonic; với Overleaf, chọn compiler XeLaTeX. Không dùng pdfLaTeX vì tài liệu có `fontspec` và Unicode tiếng Việt.

Từ thư mục gốc repo, nếu đã cài Tectonic:

```sh
tectonic --outdir bao_cao_bo_go bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.tex
```

Hoặc dùng XeLaTeX hai lần để cập nhật mục lục và tham chiếu:

```sh
xelatex -interaction=nonstopmode -halt-on-error -output-directory=bao_cao_bo_go bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=bao_cao_bo_go bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.tex
```

Báo cáo tập trung vào nguồn, định dạng, số lượng, độ dài và điểm giống/khác của 13 nhóm nhạc cụ; ba bộ A (21 chiều), B (39 chiều), C (60 chiều), công thức, giá trị thông tin và kết quả đo. Không trích dẫn slide giảng viên. Nội dung phân biệt sàng lọc tự động có bằng chứng nguồn với kiểm nghe toàn bộ; không tuyên bố đã có độ chính xác trên tập kiểm tra độc lập.

## Tái lập đặc trưng (không cần khi chỉ sửa văn bản)

Số liệu hiện hành nằm trong `../filtered_output/evidence/` và `../filtered_output/features/`. Các bản báo cáo và bộ thống kê cũ không nằm trong gói GitHub này. Không chạy trình tạo báo cáo cũ vì có thể ghi đè chỉnh sửa bằng văn bản của bạn.

- `trich_xuat_dac_trung.py`: định nghĩa thuật toán.
- `tai_lap_dac_trung_655.py`: điểm vào để chạy lại trên bộ 655 tệp hiện hành; tự tìm thư mục theo vị trí repo, không phụ thuộc đường dẫn của người tạo.
- `kiem_ke_am_thanh.py`: kiểm kê vào thư mục đầu ra do người chạy chỉ định.
- `requirements-audit.txt`: phiên bản thư viện đã dùng.

Từ thư mục gốc repo, dùng Python 3.11 trở lên:

```sh
python3 -m venv .venv-audio
.venv-audio/bin/python -m pip install -r bao_cao_bo_go/requirements-audit.txt
.venv-audio/bin/python bao_cao_bo_go/tai_lap_dac_trung_655.py
```

Trên Windows, dùng `.venv-audio\Scripts\python.exe` thay cho `.venv-audio/bin/python`. Lệnh tái lập kiểm tra tập tệp và mã băm rồi ghi lại `filtered_output/features/`; nội dung âm thanh và báo cáo `.tex` không bị sửa. Khi cập nhật số liệu trong báo cáo, lấy từ các bảng mới tương ứng.

Kiểm kê riêng mà không ghi đè hồ sơ bàn giao:

```sh
.venv-audio/bin/python bao_cao_bo_go/kiem_ke_am_thanh.py --root filtered_output --out output/audit-local
```

Một số trường metadata lưu đường dẫn gốc của lần chạy lịch sử. Không dùng các trường đó để mở audio trên máy mới; dùng `relative_path` trong kiểm kê hoặc `output` trong `accepted.csv`, tính từ `filtered_output/`.
