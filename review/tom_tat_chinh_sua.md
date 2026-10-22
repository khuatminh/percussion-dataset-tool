# Tóm tắt chỉnh sửa báo cáo (20/10/2026)

Bản sửa nằm ở `bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.tex` và `.pdf` (24 trang, biên dịch XeLaTeX không lỗi, không cảnh báo tham chiếu). Bản gốc 18 trang là commit `1f94ebc` trên nhánh `main`.

## Đã sửa

**Nội dung Yêu cầu 1**
- Thêm Bảng 2 phân loại 13 nhóm theo cách tạo âm, thay cho câu phân nhóm bị chồng lấn trước đây.
- Thêm đoạn giải thích cách gán nhãn: theo tên tệp và metadata, rồi đối chiếu bằng CLAP.
- Viết lại Mục 2.1 thành danh sách tiêu chuẩn mà cả 655 tệp đều đạt, bổ sung các ngưỡng trước đây còn thiếu (biên độ đầu tệp, số tệp tối thiểu mỗi nhóm). Theo yêu cầu của nhóm, báo cáo không nêu số tệp ứng viên hay số tệp bị loại.
- Giới thiệu CLAP: tên đầy đủ, mô hình `laion/clap-htsat-unfused`, trích dẫn, con số 617/655 tệp có nhãn đúng trong top-3, và thiên lệch có thể có khi tệp Freesound bị lọc theo CLAP.
- Viết lại câu về WAV và việc lấy mẫu lại xuống 16 kHz.
- Thêm phân tích về 92 chuỗi IDMT và việc các đoạn Iowa bị cắt ở 2 s.
- **Hình 1:** dạng sóng và phổ đồ của 13 tệp đại diện, kèm danh sách điểm giống/khác đọc từ hình (có tần số vạch cụ thể).
- **Hình 2:** biểu đồ trọng tâm phổ – độ phẳng phổ của 655 tệp.
- Thêm ghi chú rằng xylophone khác nguồn với marimba và vibraphone.

**Nội dung Yêu cầu 2**
- Định nghĩa rõ "bộ đặc trưng" và "thuộc tính" ngay từ đầu.
- Thêm Mục 6.3 đối chiếu với các nhóm đặc trưng thông dụng (ZCR, tỷ lệ im lặng, bandwidth, phân bố năng lượng) và giải thích lý do chưa dùng cao độ/độ hài hòa.
- **Bảng 10 (mới):** tỷ số Q của riêng khối thời gian và khối phổ, và Q trên 563 tệp ≤ 2 s. Bảng kèm phân tích lớp hi-hat bị tách thành hai cụm.
- **Bảng 11:** thêm cột khoảng cách tâm lớp, và viết lại phần diễn giải marimba/vibraphone.
- Thêm trích dẫn cho MFCC (Davis & Mermelstein 1980) và cho các đặc trưng phổ (Peeters 2004).

**Câu chữ và trình bày**
- Sửa các lỗi đã nêu: "nén động học", "biên cắt", "một sự kiện", "nhãn đầu tiên", "ba nhãn đầu", câu thiếu chủ ngữ. Thống nhất thuật ngữ theo quy tắc: lần đầu viết tiếng Việt kèm tiếng Anh, các lần sau chỉ dùng tiếng Việt.
- Chia báo cáo thành **Phần I: Yêu cầu 1** (Mục 1–5) và **Phần II: Yêu cầu 2** (Mục 6–12).
- Tất cả 16 bảng đều có tiêu đề đánh số. Tham chiếu mục, bảng và hình dùng `\ref`.
- Thống nhất định dạng số, ví dụ "1.261,3" và "<0,01".
- Gom các câu rào đón vào mục 13.2 "Giới hạn".
- Báo cáo được nộp như tài liệu duy nhất nên không còn tham chiếu đến tệp, đường dẫn hay tên hàm lập trình. Phụ lục cũ (danh mục tệp, tên cột, lệnh chạy) được thay bằng bảng liệt kê 60 thuộc tính của ba bộ đặc trưng; các ký hiệu clip, sgnbit, ddof, NaN/Inf, tên hàm SciPy và mã mô hình CLAP được viết lại bằng lời hoặc ký hiệu toán học. Chỉ giữ ví dụ tên tệp và mã KD/SD/HH ở Mục 1.1 để minh họa cách gán nhãn, và mã mô hình trong tài liệu tham khảo.
- Thêm trang bìa PTIT (đã điền lớp, nhóm, giảng viên, thành viên), Lời nói đầu và trang Đề bài 5 mục.
- Toàn bộ chữ (tiêu đề, chữ in đậm, liên kết, đầu trang) và khung bìa chuyển về màu đen; ô ghi chú bỏ nền, chuyển thành đoạn chữ nghiêng; tài liệu tham khảo bỏ ngày truy cập. Chỉ logo và hai hình còn màu.
- Đợt rà soát cuối: thống nhất cách gọi ZCR thuộc khối phổ của bộ A; ghi rõ 72 tệp không được CLAP xếp hạng 1 (15 Iowa, 57 IDMT); nêu tiêu chí chọn tệp đại diện; vẽ lại Hình 2 theo bốn họ; làm mềm câu về xylophone; đổi "hi-hat tiếng đơn" thành "hi-hat ngắn"; đổi tên Mục 11.2; thống nhất "hi-hat"; bỏ ngắt trang bắt buộc giữa các mục để không còn trang trống.
- Mục lục chỉ liệt kê hai Phần (in hoa), 13 mục có dòng chấm dẫn đến số trang, Phụ lục và Tài liệu tham khảo; không còn Lời nói đầu, Đề bài, Tóm tắt.
- Theo yêu cầu của nhóm, báo cáo không còn nội dung về giấy phép và về việc kiểm nghe thủ công (bỏ hai hàng ở Bảng 4, đoạn liệt kê giấy phép, gạch đầu dòng Kiểm nghe ở Giới hạn và mục hoàn tất bảng kiểm nghe ở Hướng hoàn thiện).
- 21/10/2026, theo yêu cầu của nhóm: Mục 2 không còn nhắc đến CLAP. Bước 4 đổi thành "Sàng lọc nội dung", không nêu công cụ; bỏ đoạn số liệu CLAP (583/655, 617/655, 72 tệp) và câu về độ nghiêng của phần Freesound; Mục 1.1 ghi nhãn "được xác minh và sàng lọc lại". Bỏ Bảng 4 "Kết quả kiểm tra" cùng tiêu đề Mục 2.1 và 2.2, câu về mã băm chuyển vào bước 1. Bỏ tài liệu tham khảo về CLAP (còn [1] đến [6]). Các bảng sau lùi một số (14 bảng thành 13), báo cáo còn 23 trang.
- 21/10/2026, viết lại câu chữ toàn bộ Mục 1–13 cho dễ hiểu: câu ngắn hơn, giải thích thuật ngữ ngay lần đầu (khung, bin, RMS, phổ đồ, trung vị, thang Mel), thêm ví dụ số cho các thuộc tính thời gian, thêm danh sách tám bước xử lý ở Mục 6.1 và ý nghĩa ngắn của C, F, H, L, Φ ở Mục 5.1. Bổ sung chi tiết cho Yêu cầu 3–5: Mục 10.3 (đổi tên "Sử dụng khi lưu trữ và tìm kiếm") nêu dữ liệu cần lưu, cách xử lý âm thanh truy vấn và các trường hợp đặc biệt, cách lấy top 5, đề xuất bộ A làm mặc định, nhạc cụ không có trong dữ liệu; Bảng 7 thêm cách đánh số khung và khung thay thế; Mục 8.3 và 9.2 ghi giá trị gán khi không có cặp khung hoặc delta hợp lệ; Phụ lục ghi rõ thứ tự TB/ĐLC và đó là thứ tự cột khi lưu. Kết luận thêm đoạn "Chuẩn bị cho các yêu cầu tiếp theo". Báo cáo còn 26 trang; bản trước khi viết lại nằm trong `review/ban_truoc_khi_viet_lai/`.
- 22/10/2026, viết lại Mục 13.1 Kết luận theo lối văn tự nhiên: bỏ các nhãn in đậm "Yêu cầu 1/2" và câu "đạt các tiêu chuẩn chất lượng ở Mục 2", thay bằng mô tả cụ thể (nguồn dữ liệu, không trùng, đủ dài và đủ to, không bị cắt, không méo, nhãn khớp nguồn, đã loại tệp lẫn tiếng khác); bỏ câu "vượt mức tối thiểu 500 tệp"; thêm một đoạn tóm tắt điểm giống và khác giữa các nhạc cụ; đoạn "Chuẩn bị cho các yêu cầu tiếp theo" rút gọn thành đoạn cuối. Báo cáo còn 27 trang.
- 22/10/2026, tiêu đề hai Phần bỏ chữ "Yêu cầu 1:" và "Yêu cầu 2:", nay là "Phần I. Bộ dữ liệu âm thanh nhạc cụ bộ gõ" và "Phần II. Các bộ đặc trưng nhận diện âm thanh" (cả trong Mục lục).
- 22/10/2026, theo yêu cầu của nhóm: bỏ hẳn Mục 13.2 Giới hạn và 13.3 Hướng hoàn thiện vì không phù hợp với báo cáo này; Kiểm tra tính toán thành Mục 13.2. Câu về độ hài hòa ở Mục 6.3 bỏ phần dẫn tới Mục 13. Báo cáo còn 26 trang.

**Tệp mới**
- `bao_cao_bo_go/ve_hinh_minh_hoa.py`, `bao_cao_bo_go/hinh/`
- `bao_cao_bo_go/phan_tich_bo_sung.py`, `filtered_output/features/supplementary_analysis.json`
- `review/danh_sach_uu_tien_kiem_nghe.csv`: 108 tệp nên nghe trước (CLAP xếp sai nhãn ở hạng 1 hoặc chuỗi dài hơn 2 s).

## Đính chính so với đợt review đầu
Đợt review đầu đã nghi rằng các chuỗi IDMT dài làm bộ A tách lớp "đẹp" nhờ cách cắt tệp. Kiểm tra lại cho thấy **nghi ngờ đó không đúng**: riêng 5 thuộc tính thời gian chỉ đạt Q = 1,35, còn 16 thuộc tính phổ đạt Q = 1,93. Khi bỏ các chuỗi dài, thứ tự A > C > B vẫn giữ nguyên. Ảnh hưởng thật của dạng bản ghi là lớp hi-hat bị tách thành hai cụm, và báo cáo đã ghi điều này ở Mục 11.2.

## Nhóm còn phải tự làm
1. (Không bắt buộc) Nghe kiểm tra các tệp theo `filtered_output/evidence/listening_checklist.csv`, ưu tiên 108 tệp trong `review/danh_sach_uu_tien_kiem_nghe.csv`. Báo cáo hiện không nhắc đến việc kiểm nghe.
2. Kiểm tra lại tên khoa và tên đề tài trên trang bìa.
3. (Không bắt buộc) Tách chuỗi IDMT thành từng tiếng gõ, bổ sung mẫu cho các lớp ít dữ liệu, thêm thuộc tính độ hài hòa. Những việc này làm thay đổi dữ liệu và toàn bộ số liệu, nên chưa thực hiện.
