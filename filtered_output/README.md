# Bộ dữ liệu âm thanh bộ gõ đã chọn lọc

Phiên bản 20/10/2026: **655 file thuộc 13 nhóm nhạc cụ**.

Đây là bộ hiện hành trong `filtered_output/accepted`. Đã kiểm tra lại tín hiệu và chạy CLAP trên 1.251 ứng viên trước khi chọn. Giữ 655 file đáp ứng các quy tắc sàng lọc dưới đây, vượt yêu cầu 500 file; không thêm các ứng viên yếu hơn chỉ để làm tròn 700.

## Thành phần

| Nhãn | Số file |
|---|---:|
| agogo | 16 |
| claves | 13 |
| conga | 18 |
| cowbell | 43 |
| cymbal | 33 |
| hi_hat | 93 |
| kick | 151 |
| marimba | 36 |
| snare | 141 |
| tambourine | 12 |
| tom | 76 |
| vibraphone | 12 |
| xylophone | 11 |
| **Tổng** | **655** |

Nguồn: 513 Freesound One-Shot, 94 IDMT-SMT-Drums, 48 Iowa MIS. Không còn mẫu ghi nguồn giấy phép `unknown`.

Các nhóm djembe, castanets và gong không còn trong phiên bản này: djembe không đủ hỗ trợ kết hợp của bộ lọc; castanets/gong còn quá ít ứng viên sau lọc (dưới 5 mẫu/lớp). Việc bỏ nhóm là lựa chọn xây dựng dataset, không chứng minh toàn bộ âm thanh gốc trong nhóm sai. Bangu/timbales gộp trong tom không được giữ.

## Kết quả kiểm tra kỹ thuật

- 655/655 file đọc trọn vẹn, không rỗng, không có NaN/Inf.
- Toàn bộ WAV PCM 16-bit, mono, 16.000 Hz.
- Không có file trùng byte hoặc trùng PCM chính xác.
- Thời lượng 0.107438–20.614687 giây; trung vị 0.534062 giây.
- Tổng thời lượng 1583.158 giây (~26 phút 23 giây).
- Dung lượng audio 50,689,868 byte (48.34 MiB).
- Không còn file dưới 100 ms, hoạt động âm dưới 50 ms, peak nhỏ hơn -40 dBFS, cờ tiếp giáp đầu/đuôi theo phép kiểm hiện tại, hoặc cờ clipping của bộ lọc kỹ thuật.
- Hash và nhãn thư mục khớp đủ 655 hàng metadata. Các file giữ nguyên audio, không tăng gain, cắt hoặc resample trong lần chọn này.

## Quy tắc lựa chọn và mức bằng chứng

1. Nguồn/giấy phép có thông tin; tên và nhãn không có vấn đề phân nhóm chưa giải quyết.
2. Không có cờ tín hiệu theo ngưỡng công bố trong `evidence/selection_summary.json`. Đây là ngưỡng chọn bảo thủ, không phải ngưỡng bắt buộc của đề.
3. Freesound: ID, tên, tác giả và giấy phép khớp metadata chính thức; CLAP top-1 trùng nhãn (513 mẫu).
4. IDMT: 94 mẫu có đối chiếu dạng sóng với audio nguồn chính thức, cosine sau quy đổi tần số >0,99; nguồn là file huấn luyện từng nhạc cụ hoặc track tách riêng.
5. Iowa: tên nguồn thuộc đúng nhạc cụ và nhãn nằm trong top-3 CLAP (48 mẫu). Chưa đối chiếu dạng sóng với audio gốc cho nhóm này.
6. Bỏ ứng viên có dấu hiệu mơ hồ về tiếng nói/nhạc phối/hiệu ứng nhiễu trong phép so khớp mô tả, và các nhóm còn dưới 5 mẫu. Không dùng điểm “mixed_drums” để tự kết luận nhiều nhạc cụ vì phép dò này đã bộc lộ sai lệch trên nguồn IDMT.

**Giới hạn cần ghi đúng:** 583/655 mẫu có top-1 mô hình trùng nhãn; 72 mẫu còn lại được giữ nhờ bằng chứng nguồn theo quy tắc IDMT/Iowa. Không coi cosine hoặc mức đồng thuận là xác suất đúng. Chưa kiểm nghe độc lập toàn bộ tập nên `single_instrument_verified=no` vẫn được giữ. Không khẳng định 655 file đã được con người xác nhận “mỗi file chỉ một nhạc cụ” hoặc đủ nhận diện trong mọi trường hợp.

## Mô tả và đặc trưng

Các nhãn gồm trống, gõ gỗ, gõ kim loại và nhạc cụ gõ có cao độ. Chúng được mô tả thống nhất bằng thời gian hoạt động, đường bao năng lượng và phân bố năng lượng theo tần số. Bảng sau đo trực tiếp trên tập 655 file:

| Nhãn | Thời lượng trung vị (s) | Tâm phổ công suất trung vị (Hz) | Tỷ lệ năng lượng dưới 500 Hz, trung vị |
|---|---:|---:|---:|
| agogo | 0.673 | 1322.4 | 0.000 |
| claves | 0.209 | 2693.7 | 0.000 |
| conga | 0.476 | 252.1 | 0.987 |
| cowbell | 0.232 | 612.5 | 0.452 |
| cymbal | 0.766 | 3234.3 | 0.043 |
| hi_hat | 5.647 | 4437.9 | 0.078 |
| kick | 0.480 | 74.6 | 0.998 |
| marimba | 2.000 | 525.7 | 0.262 |
| snare | 0.464 | 1474.2 | 0.469 |
| tambourine | 0.395 | 5805.7 | 0.000 |
| tom | 0.720 | 192.7 | 0.976 |
| vibraphone | 2.000 | 573.0 | 0.122 |
| xylophone | 0.510 | 1574.1 | 0.177 |

Ba bộ đặc trưng đã **tính lại trên đúng 655 file**:

- A: 21 thuộc tính về thời gian và phổ.
- B: 39 thuộc tính MFCC và biến thiên thời gian.
- C: 60 thuộc tính kết hợp, chuẩn hóa lại trên tập hiện tại.

`sample_id` trong các bảng đặc trưng khớp `index` của `evidence/inventory.csv`. Các giá trị đều hữu hạn; không dùng lại bộ chuẩn hóa 1.251 mẫu.

## Cách sử dụng

- `accepted/`: duy nhất 655 audio dùng cho bộ dữ liệu hiện hành.
- `accepted.csv` và `manifest.csv`: cùng mô tả tập hiện hành; cột `output` là đường dẫn tương đối từ `filtered_output`.
- `summary.json`: thống kê mới, không còn số 5.589/1.251 trong số lượng dataset hiện hành.
- `evidence/`: kiểm kê, SHA-256, quy tắc chọn, bằng chứng nhãn/nguồn và bảng đối chiếu IDMT.
- `features/`: các bảng đặc trưng đã tính lại.

Ví dụ Python: `audio_path = Path("filtered_output") / row["output"]`.
Các trường `source_original_metadata_path` là dấu vết đường dẫn lịch sử của nguồn, không phải đường dẫn để mở bản audio hiện hành.

## Bản trước và tài liệu cũ

Bản trước của toàn bộ `filtered_output` được chuyển sang `output/dataset_archive_2026-10-20/before_selection`, ngoài bộ hiện hành. Trong đó có 596 ứng viên accepted không được chọn, các vùng review/accepted_removed/unfiltered và metadata cũ. Có thể phục hồi trên máy tạo dữ liệu; không xóa vĩnh viễn dữ liệu. Thư mục lưu trữ lịch sử này chỉ có ở máy tạo và không được đưa lên GitHub.

Báo cáo hiện hành là `../bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.tex` và [`bao_cao_mmdb_yeu_cau_1_2.pdf`](../bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.pdf), đã cập nhật đúng **655 file, 13 nhóm** và ba bộ đặc trưng. Các báo cáo khác và các bảng trong `bao_cao_bo_go/evidence`, `bao_cao_bo_go/features` là tài liệu lịch sử của phiên bản trước, chỉ lưu tại máy tạo và không đưa lên GitHub. Không dùng chúng thay cho số liệu hiện hành trong thư mục này.

Nguồn tham chiếu: [Freesound](https://zenodo.org/records/4687854), [IDMT](https://www.idmt.fraunhofer.de/en/publications/datasets/drums.html), [Iowa MIS](https://theremin.music.uiowa.edu/MIS.html), [CLAP](https://huggingface.co/laion/clap-htsat-unfused).
