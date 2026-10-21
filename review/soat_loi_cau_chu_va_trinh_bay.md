# Soát lỗi câu chữ, diễn giải và trình bày

Bổ sung cho [review_bao_cao_muc_1_2.md](review_bao_cao_muc_1_2.md). Số dòng ghi theo file `bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.tex`.

**Đã kiểm tra và không thấy sai:**
- Mọi con số trong báo cáo khớp với `filtered_output/`: số tệp từng lớp, thời lượng, dung lượng, 514 tệp ≤ 1 s, 583/655, các Bảng 2–5, IDMT 56 + 38.
- Mọi công thức ở Mục 6–12 khớp với `trich_xuat_dac_trung.py`: khung, Hann, FFT, rolloff, flatness, entropy, ZCR, flux, Mel HTK, DCT ortho, delta, chuẩn hóa, $d_C^2 = \tfrac12 d_A^2 + \tfrac12 d_B^2$, $Q$, $J_j$.
- Bản PDF khớp với nguồn `.tex` hiện tại.

Các lỗi còn lại chủ yếu nằm ở **cách diễn giải**, **thông tin bị thiếu** và **câu chữ**.

---

## A. Lỗi diễn giải và thông tin thiếu (nên sửa)

### A1. Đọc sai cặp marimba/vibraphone ở bộ B (Mục 11.2, dòng 466)
Câu hiện tại viết: "Trong B, hi-hat/tambourine gần hơn agogo/cowbell và marimba/vibraphone." Câu này đúng theo số trong Bảng 4, nhưng dễ dẫn đến kết luận sai rằng MFCC coi marimba và vibraphone rất khác nhau.
- Bảng 4 dùng *trung bình khoảng cách mọi cặp tệp*, nên con số đã bao gồm cả độ phân tán *bên trong* mỗi lớp. Tính lại trên bộ B, khoảng cách trong lớp của marimba là 1,96 và của vibraphone là 2,10, cao nhất trong 13 lớp.
- Khi xét khoảng cách giữa **tâm lớp** (đã có sẵn cột `centroid_distance` trong `features/class_pair_distances.csv`), lớp gần vibraphone nhất lại chính là marimba (0,84).
- Cách sửa: thêm cột khoảng cách tâm vào Bảng 4, hoặc viết lại câu: *"Khoảng cách trung bình marimba/vibraphone trong B lớn chủ yếu vì hai lớp này phân tán mạnh bên trong (MFCC thay đổi theo cao độ nốt). Xét khoảng cách giữa tâm lớp, marimba vẫn là lớp gần vibraphone nhất."* Câu này còn củng cố nhận xét về ảnh hưởng của cao độ ở Mục 9.3.

### A2. Thiếu số liệu của quá trình tuyển chọn (Mục 2.1)
Báo cáo không nói bộ dữ liệu được lọc từ bao nhiêu tệp. Theo `evidence/selection_summary.json`, nhóm đã **sàng lọc 1.251 tệp, giữ 655 và loại 596**. Nên thêm một câu hoặc một hàng trong bảng 2.2 để thể hiện công sức "xây dựng/sưu tầm".

Cũng trong file đó có các ngưỡng mà báo cáo chưa nêu: `max_start_sample_to_peak = 0.1`, `min_class_count = 5`, `max_candidate_count = 700`. Nếu các ngưỡng này đã được áp dụng thì nên mô tả trong bước 2 của Mục 2.1.

### A3. Chưa nói nhãn được gán bằng cách nào (Mục 1.1 hoặc 2.1)
Cả 655 tệp có `label_origin = metadata_or_filename_rule`, tức nhãn lấy theo quy tắc từ tên tệp và metadata nguồn (ví dụ `cymbal (crash)` được gán thành `cymbal`), sau đó mới đối chiếu với CLAP. Báo cáo chưa có câu nào nói điều này. Nên thêm một câu.

### A4. CLAP chưa được giới thiệu và chưa có trích dẫn (dòng 137–140)
- Lần đầu nhắc tới cần viết tên đầy đủ: *CLAP (Contrastive Language–Audio Pretraining)*. Nên ghi cả mô hình đã dùng là `laion/clap-htsat-unfused` (theo `evidence/model_run_config.json`) và thêm vào tài liệu tham khảo: Y. Wu et al., "Large-scale Contrastive Language-Audio Pretraining with Feature Fusion and Keyword-to-Caption Augmentation", ICASSP 2023.
- Nên thêm một câu vào phần giới hạn. Toàn bộ 513 tệp Freesound được giữ lại *vì* CLAP xếp đúng nhãn ở hạng 1, nên phần dữ liệu này có thể nghiêng về các mẫu "điển hình", dễ nhận diện. Điều đó có thể làm các tỷ số tách lớp ở Mục 11 đẹp hơn thực tế.

### A5. Xylophone khác nguồn với marimba và vibraphone (Mục 5.2, dòng 258)
Xylophone lấy từ Freesound, còn marimba và vibraphone đều từ Iowa. Câu "Khoảng cao độ và cách trích mẫu có thể góp phần tạo chênh lệch" nên nói thẳng là **khác nguồn thu**, vì đây là lý do lớn nhất khiến trọng tâm phổ chênh 1.889 Hz so với 245 Hz.

### A6. Câu "WAV không nén mất dữ liệu" dễ hiểu nhầm (dòng 125)
Câu này có thể bị đọc thành "WAV không nén, mất dữ liệu". Ngoài ra, việc lấy mẫu lại từ 44,1 kHz xuống 16 kHz thực tế đã làm mất thông tin. Đề xuất: *"WAV PCM không nén nên định dạng lưu không làm mất thêm thông tin; tuy nhiên bước lấy mẫu lại xuống 16 kHz đã loại các thành phần trên 8 kHz."*

### A7. Giấy phép IDMT là CC BY-NC-ND 4.0 (dòng 122)
"ND" nghĩa là không được phân phối bản phái sinh. 94 tệp IDMT đã được đổi tần số lấy mẫu. Nếu repo GitHub chứa các tệp này ở chế độ công khai thì có rủi ro vi phạm giấy phép. Đây không phải lỗi của báo cáo, nhưng nên để repo ở chế độ riêng tư hoặc không đưa các tệp IDMT lên.

---

## B. Câu chữ và thuật ngữ

| Dòng | Hiện tại | Đề xuất |
|---|---|---|
| 314 | "nén động học" | **"nén dải động (dynamic range compression)"**. "Động học" là thuật ngữ cơ học, dùng ở đây là sai. |
| 135, 190 | "biên cắt" (nghĩa mơ hồ) | Tách thành "tiếng bị cắt cụt ở đầu/cuối tệp" và "cắt ngọn (clipping)". |
| 120 | "tập tiếng bộ gõ một sự kiện" | "tập tiếng bộ gõ dạng một lần gõ (one-shot)" |
| 137 | "Freesound được giữ khi nhãn đầu tiên phù hợp metadata" | "Tệp Freesound được giữ khi nhãn CLAP xếp hạng 1 trùng với nhãn lấy từ metadata" |
| 137 | "Iowa dựa trên tên nguồn và hỗ trợ trong ba nhãn đầu" | "Tệp Iowa được giữ dựa trên tên nhạc cụ của nguồn và khi nhãn đó nằm trong ba nhãn CLAP xếp cao nhất" |
| 137 | "Loại các trường hợp mơ hồ theo quy tắc tuyển chọn." | Nêu rõ thế nào là "mơ hồ" và loại bao nhiêu tệp (xem A2). |
| 190 | "…kỹ thuật biểu diễn; không suy ra chỉ từ thời lượng tổng." (câu thiếu chủ ngữ) | "…kỹ thuật biểu diễn, nên không thể đánh giá chỉ bằng tổng thời lượng." |
| 104 | "Các nhóm gồm trống màng rung, nhạc cụ kim loại, thanh gõ và nhạc cụ gõ có cao độ." (các nhóm chồng lấn nhau, vì xylophone cũng là thanh gõ) | Phân loại rõ, nên làm thành bảng: **màng rung** (kick, snare, tom, conga); **tự thân vang, kim loại** (hi-hat, cymbal, cowbell, agogo; tambourine có cả màng và kim loại); **tự thân vang, gỗ** (claves); **có cao độ xác định** (marimba, xylophone, vibraphone). |
| 386 | "equalizer" | "bộ cân bằng tần số (EQ)" |
| 314, 502 | "Crest lớn…", "Thời gian, crest" | Dùng thống nhất "hệ số đỉnh" như tiêu đề 7.2. |
| 504 | "Độ rộng, flatness, entropy" | "Độ rộng, độ phẳng, entropy phổ" |
| 308, 521 | "decay", "attack" | "suy giảm", "khởi âm". Chỉ ghi tiếng Anh trong ngoặc ở lần đầu. |

**Quy tắc chung nên áp dụng:**
- Lần đầu nhắc tới một khái niệm thì viết *tiếng Việt (tiếng Anh)*, sau đó chỉ dùng tiếng Việt. Hiện báo cáo trộn lẫn crest/hệ số đỉnh, flatness/độ phẳng, training/isolated tracks, gain, metadata.
- "Đặc trưng" và "thuộc tính" đang được dùng lẫn lộn. Đề bài dùng cả hai từ. Nên định nghĩa một lần ở Mục 6, ví dụ "mỗi *bộ đặc trưng* là một vector gồm nhiều *thuộc tính* (chiều)", rồi giữ nguyên cách dùng đó.
- Báo cáo có quá nhiều câu rào đón dạng "không phải…/không đồng nghĩa…/chưa được coi là…", gần như đoạn nào cũng có. Nên giữ các ý quan trọng và gom vào một mục "Giới hạn" ở cuối.

---

## C. Trình bày

1. **Cấu trúc không bám theo đề.** Chỉ Mục 1 có chữ "Yêu cầu 1" và chỉ Mục 6 có chữ "Yêu cầu 2", trong khi Yêu cầu 1 thực ra trải từ Mục 1 đến 5 và Yêu cầu 2 từ Mục 6 đến 12. Người chấm dễ hiểu nhầm rằng Yêu cầu 1 chỉ gồm Mục 1. Nên chia thành **Phần I: Yêu cầu 1** và **Phần II: Yêu cầu 2**, hoặc đổi tên Mục 1 thành "Nguồn và định dạng dữ liệu".
2. **Chỉ 5 bảng có tiêu đề đánh số** (Bảng 1–5). Các bảng còn lại không có `\caption`: bảng đối chiếu đề bài, bảng nguồn, bảng kết quả kiểm tra, bảng 13 nhóm nhạc cụ, bảng thiết lập khung, bảng tương đồng/khác biệt và bảng phụ lục. Nên thêm caption để đánh số liên tục và tham chiếu được.
3. **Định dạng số chưa thống nhất.** Bảng 2 ghi "4429,7" và "1261,3", còn phần văn bản ghi "4.429,7". Cột $L$ của agogo và claves hiện là "0,00" trong khi văn bản nói "0,002%". Nên ghi "<0,01" hoặc thêm chữ số thập phân.
4. **Tham chiếu mục đang viết tay** ("Mục 5", "Mục 6--8", "Mục 7--12" trong bảng tóm tắt). Khi thêm hình hoặc thêm mục, các số này sẽ bị lệch. Nên đặt `\label` cho từng mục và dùng `\ref`.
5. **Dòng 561** ghi `features/class_feature_medians.csv` mà thiếu tiền tố `filtered_output/`, không giống các đường dẫn khác trong bảng phụ lục.
6. **Trang bìa** còn thiếu tên trường/khoa, tên học phần, giảng viên, số nhóm và danh sách thành viên (hiện chỉ có một ô và đang để trống).
7. **Tài liệu tham khảo** chỉ có 4 mục, toàn là nguồn dữ liệu và SciPy. Nên thêm nguồn cho định nghĩa đặc trưng: S. Davis & P. Mermelstein (1980) cho MFCC, G. Peeters (2004) "A large set of audio features for sound description" cho các đặc trưng phổ, và CLAP (xem A4).
