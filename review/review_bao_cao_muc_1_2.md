# Review báo cáo Yêu cầu 1 và 2

Bản được review: `percussion-dataset-tool/bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.tex` (18 trang, 655 tệp, 13 nhóm). Các số liệu chính đã được đối chiếu với `filtered_output/accepted.csv`, `evidence/` và `features/`.

## Kết luận nhanh

| Yêu cầu đề bài | Đánh giá | Ghi chú |
|---|---|---|
| ≥ 500 tệp bộ gõ | **Đạt** | 655 tệp, đếm lại từng thư mục khớp bảng trong báo cáo. |
| Độ dài phù hợp | **Đạt một phần** | Đa số là tiếng gõ đơn ngắn. Có 92 tệp dài hơn 2 s là chuỗi nhiều lần đánh (xem mục 2 bên dưới). |
| Mỗi tệp chỉ một nhạc cụ | **Chưa chứng minh được** | Chính báo cáo ghi 0/655 tệp đã kiểm nghe; `listening_checklist.csv` còn trống. |
| Định dạng tự chọn | **Đạt** | WAV PCM 16-bit mono 16 kHz, có giải thích lý do. |
| Mô tả giống/khác nhau | **Đạt, nên bổ sung hình** | Có bảng mô tả 13 nhóm và bảng số đo; chưa có hình phổ hoặc dạng sóng nào. |
| Xây dựng bộ đặc trưng | **Đạt tốt** | 3 bộ A (21), B (39), C (60), công thức rõ, tái lập được. |
| Đặc trưng cho tương đồng và khác biệt | **Đạt tốt** | Có khoảng cách trong/giữa lớp, bảng cặp nhạc cụ, bảng "tương đồng / khác biệt". |
| Giá trị thông tin của đặc trưng | **Đạt tốt** | Mỗi đặc trưng đều có phần "giá trị thông tin" và chỉ số J để xếp hạng. |

Nhìn chung báo cáo đã đủ nội dung cho mục 1 và 2, phần đặc trưng làm kỹ hơn mức đề bài yêu cầu. Điểm yếu lớn nhất nằm ở mục 1: báo cáo tự ghi rằng điều kiện "mỗi tệp chỉ gồm tiếng một nhạc cụ" chưa được xác nhận. Người chấm đọc đến đó sẽ hiểu là yêu cầu chưa đạt.

## Cần sửa trước khi nộp (theo thứ tự ưu tiên)

### 1. Kiểm nghe tệp để xác nhận "một nhạc cụ mỗi tệp"
- Hiện trạng: bảng ở Mục 2.2 ghi "Tệp đã được xác nhận kiểm nghe thủ công: 0", cột `single_instrument_verified` = `no` cho cả 655 tệp, và ghi chú cuối Mục 2 nói rõ là chưa hoàn tất.
- Tổng thời lượng chỉ khoảng 26 phút 23 giây, nên nhóm chia nhau nghe hết là làm được. Danh sách `filtered_output/evidence/listening_checklist.csv` đã có sẵn cột `single_instrument`, `attack_and_decay_sufficient`, `label_correct`.
- Nên nghe kỹ trước nhóm rủi ro: 46/93 tệp hi-hat có nhãn CLAP hạng 1 khác hi-hat (24 tệp CLAP đoán là snare, phần lớn là chuỗi IDMT), cùng 72 tệp không được CLAP xếp đúng hạng 1 nói chung.
- Sau khi nghe xong, sửa bảng (0 thành số tệp đã nghe), bỏ các câu "chưa hoàn tất kiểm nghe" ở phần Tóm tắt, Mục 2 và Mục 13, rồi loại hoặc thay các tệp không đạt.

### 2. Chuỗi dài từ IDMT làm lệch đặc trưng thời gian
- 92 tệp dài hơn 2 s đều là chuỗi IDMT: 53 hi-hat, 31 kick, 8 snare. Riêng hi-hat chiếm khoảng 700/1583 s tổng thời lượng, trung vị là 5,6 s.
- Hệ quả là các thuộc tính a1, a2, a4, a5 của bộ A có thể tách hi-hat ra nhờ *cách cắt tệp* chứ không phải nhờ âm sắc. Điều này cũng làm giảm sức thuyết phục của kết luận "A tách lớp tốt nhất".
- Có hai cách xử lý. Cách tốt hơn là cắt các chuỗi IDMT thành từng tiếng gõ đơn bằng phát hiện onset rồi trích lại đặc trưng. Cách nhẹ hơn là giữ nguyên dữ liệu nhưng thêm một đoạn ngắn thừa nhận ảnh hưởng này khi bàn về kết quả Q ở Mục 11.
- Vibraphone có 12/12 tệp dài đúng 2,000 s và marimba có trung vị 2,000 s, tức phần ngân bị cắt cụt. Nên nói rõ việc này trong phần "độ dài phù hợp" hoặc trích đoạn dài hơn.

### 3. Thêm hình minh họa cho phần mô tả giống/khác (Mục 4–5)
- Báo cáo hiện không có hình nào. Một lưới 13 ô gồm dạng sóng và spectrogram của một tệp đại diện mỗi nhóm (`evidence/representative_files.csv` đã có sẵn danh sách) sẽ làm phần "mô tả đặc điểm giống và khác nhau" thuyết phục hơn nhiều. Bài giảng 10 cũng dùng spectrogram để minh họa tiếng trống.
- Bảng 13 nhóm ở Mục 4.2 đang được viết là "dấu hiệu dự kiến… không phải biên bản đã nghe". Sau khi kiểm nghe, nên viết lại thành những gì nhóm đã quan sát được.

## Nên bổ sung (giúp điểm cao hơn)

4. **Cao độ / tính hài hòa (pitch, harmonicity).** Bài giảng 10 liệt kê các đặc trưng miền thời gian (energy, ZCR, silence ratio) và miền tần số (bandwidth, energy distribution, harmonicity, pitch). Báo cáo đã có gần hết các đặc trưng đó, nhưng thiếu harmonicity và pitch. Đây lại chính là đặc trưng phân biệt nhạc cụ có cao độ (marimba, vibraphone, xylophone, cowbell, agogo) với trống và cymbal. Nên thêm 1–2 thuộc tính (ví dụ độ hài hòa từ tự tương quan và f0), hoặc ít nhất giải thích vì sao không dùng.
5. **Gọi tên theo thuật ngữ môn học.** `active_fraction` gần với 1 − *silence ratio*, `độ rộng phổ` chính là *bandwidth*, `L` là *energy distribution*. Nêu các tương ứng này trong một câu sẽ giúp người chấm nhận ra ngay.
6. **Mất cân bằng lớp.** Xylophone có 11 tệp, tambourine và vibraphone 12, claves 13, trong khi kick có 151 và snare 141. Báo cáo đã nhắc tới, nhưng nếu còn thời gian thì nên bổ sung để mỗi lớp có ít nhất khoảng 30 tệp.
7. **Tần số lấy mẫu 16 kHz.** Mức này bỏ mất mọi thành phần trên 8 kHz của cymbal, hi-hat và tambourine. Báo cáo đã thừa nhận điều này, nhưng 22,05 hoặc 44,1 kHz sẽ hợp lý hơn với tiếng kim loại. Không bắt buộc phải đổi.

## Lỗi hình thức nhỏ
- Trang bìa chỉ có một ô Họ tên/MSSV/Lớp và hiện để trống. Báo cáo nhóm nên có danh sách thành viên, có thể kèm phân công.
- Giọng văn có rất nhiều câu rào đón kiểu "không phải…", "không đồng nghĩa…", "chưa được coi là…". Một vài câu là cần thiết, nhưng mật độ hiện tại khiến báo cáo đọc như đang tự phòng thủ. Nên gom lại vào một mục "Giới hạn" thay vì rải ở mọi đoạn.
- Mục 10.3 (sử dụng trong CSDL, truy vấn) đã chạm sang yêu cầu 3–4. Giữ ngắn như hiện tại là ổn.

## Những điểm đã làm tốt
- Nguồn dữ liệu rõ ràng (Freesound 513, IDMT 94, Iowa 48), có giấy phép theo từng tệp, có loại trùng bằng SHA-256.
- Công thức đặc trưng đầy đủ và chính xác, nêu rõ tham số (khung 25 ms, bước 10 ms, FFT 512, 40 bộ lọc Mel, DCT-II ortho), tái lập được bằng mã đi kèm.
- Có lập luận định lượng cho cả tương đồng lẫn khác biệt: D_trong, D_ngoài, Q, bảng cặp lớp, chỉ số J. Phần này đáp ứng đúng ý "giá trị thông tin của các đặc trưng".
- Chuẩn hóa và cân bằng khối A/B trong bộ C có giải thích toán học rõ ràng.
