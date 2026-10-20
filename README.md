# Bộ dữ liệu bộ gõ và báo cáo yêu cầu 1–2

Repo gồm **655 tệp âm thanh / 13 nhóm nhạc cụ**, báo cáo LaTeX/PDF, các bảng đặc trưng và mã xử lý. Đây là phiên bản tuyển chọn ngày 20/10/2026.

## Bắt đầu chỉnh sửa báo cáo

1. Clone repo (cần quyền truy cập vì repo private):
   ```sh
   git clone https://github.com/khuatminh/percussion-dataset-tool.git
   cd percussion-dataset-tool
   git switch -c chinh-sua-bao-cao
   ```
2. Sửa trực tiếp [`bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.tex`](bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.tex). Đây là nguồn báo cáo chính, độc lập và đã nhúng các bảng. Điền `HoTen`, `MSSV`, `Lop` trong phần đầu nếu cần.
3. Xem [bản PDF hiện tại](bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.pdf). Để biên dịch, dùng **XeLaTeX** với bộ TeX đầy đủ hoặc **Tectonic**; không dùng pdfLaTeX. Có thể tải riêng `.tex` lên Overleaf và chọn XeLaTeX.
   ```sh
   tectonic --outdir bao_cao_bo_go bao_cao_bo_go/bao_cao_mmdb_yeu_cau_1_2.tex
   ```
4. Commit thay đổi trên nhánh riêng, push và tạo pull request để cùng xem lại. Không cần chạy lại lọc âm thanh khi chỉ sửa văn bản báo cáo.

## Các file cần dùng

| Đường dẫn | Nội dung |
|---|---|
| [`bao_cao_bo_go/`](bao_cao_bo_go/README.md) | Báo cáo hiện hành và hướng dẫn tái lập |
| [`filtered_output/accepted/`](filtered_output/accepted/) | Đủ 655 WAV, chia theo 13 nhãn |
| [`filtered_output/accepted.csv`](filtered_output/accepted.csv) | Metadata, nguồn, giấy phép và đường dẫn audio |
| [`filtered_output/evidence/`](filtered_output/evidence/) | Kiểm kê, mã băm, bằng chứng tuyển chọn và danh sách kiểm nghe |
| [`filtered_output/features/`](filtered_output/features/) | Bộ A 21 chiều, B 39 chiều, C 60 chiều và các thống kê |
| [`filtered_output/README.md`](filtered_output/README.md) | Quy tắc chọn và giới hạn của dữ liệu |

Repo giữ giấy phép theo từng tệp nguồn, không gán một giấy phép chung mới cho audio. Dữ liệu được sàng lọc kỹ thuật và đối chiếu nguồn; chưa ghi nhận kiểm nghe thủ công toàn bộ 655 tệp. Các đường dẫn tuyệt đối trong hồ sơ lịch sử chỉ ghi nguồn gốc lần chạy, không cần có trên máy người clone; mở audio bằng đường dẫn `output` tương đối từ `filtered_output/`.

## Công cụ lọc dữ liệu nguồn

Phần dưới mô tả công cụ lọc ban đầu. Bộ 655 tệp bàn giao đã qua thêm bước tuyển chọn; không ghi đè `filtered_output/` khi thử công cụ.

Tool Python chạy offline trên máy, quét thư mục con và **sao chép**, không xóa hay sửa file gốc. Hợp với Freesound One-Shot Percussive Sounds và các bộ có tên nhạc cụ trong tên file/thư mục.

## Cài đặt và chạy

Python 3.10 trở lên. Trong thư mục dự án:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python percussion_filter.py --input "/duong/dan/thu-muc-am-thanh" --output "output/lan-1"
```

Trên Windows dùng `py -m venv .venv` và `.venv\Scripts\activate` thay cho hai lệnh đầu. Luôn đặt đường dẫn có khoảng trắng trong dấu ngoặc kép.

Nếu đang dùng máy Mac hiện tại, môi trường `.venv` đã được cài sẵn. Có thể gọi `.venv/bin/python percussion_filter.py ...` trực tiếp, không cần activate.

Đầu vào là thư mục đã giải nén; tool không mở ZIP. Đầu ra phải là thư mục **chưa tồn tại**; mỗi lần chạy chọn một tên mới. Không bắt buộc độ dài 1 giây, không có giới hạn độ dài tối đa mặc định. Không tự cắt nốt, thay đổi âm lượng, lấy mẫu lại hay thêm khoảng lặng.

## Freesound: quan trọng khi file chỉ có tên số

Tải `one_shot_percussive_sounds.zip` cùng **`licenses.txt`** tại:
https://zenodo.org/records/4687854

`licenses.txt` của bộ này có nội dung JSON, chứa tên âm thanh gốc, tác giả và giấy phép theo ID. Đây là thông tin cần thiết để suy nhãn cho `102780.wav`... Chỉ nhìn ID không thể biết nhạc cụ.

```sh
python percussion_filter.py \
  --input "data/one_shot_percussive_sounds" \
  --metadata "data/licenses.txt" \
  --output "output/freesound-1"
```

Có thể bổ sung `--metadata "data/sound_info_analysis.json"` nếu đã tải metadata mở rộng. Tham số `--metadata` có thể dùng nhiều lần. Hỗ trợ JSON theo ID, danh sách bản ghi JSON, JSON có trường `results`, hoặc CSV. CSV nên có `file` (đường dẫn tương đối), `name`, `tags`, `license`, `username`, `url`. Metadata sau bổ sung/ghi đè trường của metadata trước.

## Đầu ra

```text
output/freesound-1/
  accepted/                  # Qua kiểm tra tín hiệu và có nhãn văn bản không xung đột
    kick/
    snare/
    hi_hat/
    marimba/
    ...
  review/                    # Cần nghe/kiểm tra, chưa đưa vào dataset chính
    unknown/
    snare/
    ...
  manifest.csv               # Tất cả file, chỉ số, nhãn, bằng chứng, lý do, đường dẫn
  accepted.csv
  review.csv
  rejected.csv               # File lỗi/im lặng/quá ngắn; không sao chép
  duplicate.csv              # File trùng; chỉ giữ một đại diện
  copy_error.csv             # Lỗi sao chép nếu có
  overrides_template.csv     # Mẫu sửa nhãn bằng tay
  summary.json               # Thống kê từng lớp và đã đủ 500 file accepted hay chưa
```

Tên file xuất có tiền tố mã đường dẫn để tránh trùng tên. Nội dung audio và định dạng giữ nguyên. Các thư mục âm thanh chỉ được tạo khi có file tương ứng. `--dry-run` chỉ ghi CSV/JSON, không sao chép audio; cột `output` lúc này là đường dẫn dự kiến.

## “Valid” được kiểm tra như thế nào?

1. Đọc giải mã toàn bộ file bằng SoundFile; phát hiện file không đọc được, rỗng hoặc chứa NaN/Inf.
2. Loại file dưới **0,02 giây** hoặc có ít hơn **0,01 giây** hoạt động âm thanh theo cửa sổ 10 ms. Đây là ngưỡng kỹ thuật có thể đổi, không phải kết luận rằng mọi tiếng gõ dưới 20 ms là vô dụng.
3. Loại tín hiệu có peak không vượt **−70 dBFS**. Thời gian hoạt động được ước lượng bằng RMS trên các kênh, ngưỡng lớn hơn giữa −70 dBFS và peak −40 dB; file rất nhỏ có thể cần điều chỉnh.
4. Đưa vào `review` nếu hơn 1% mẫu gần biên toàn thang (nghi clipping), tần số lấy mẫu dưới 16 kHz hoặc cuối file còn mạnh (có thể bị cắt đuôi). Các dấu hiệu này chỉ là cảnh báo, không khẳng định file hỏng.
5. Dò nhãn bằng từ khóa có ranh giới từ trong đường dẫn **tương đối**, tên gốc và tags/nhãn của metadata. Không dùng username hay mô tả tự do làm nhãn. Nhận nhiều nhạc cụ hoặc dấu hiệu drum kit/drum loop → `review`; không có nhãn → `review/unknown`.
6. So SHA-256 của file và tín hiệu PCM đã giải mã, kèm sample rate/số kênh. Loại trùng chính xác cả khi khác container nhưng PCM giống nhau. Không phát hiện tất cả bản gần trùng, tăng/giảm âm lượng hoặc đã resample. Hai bản trùng nhưng nhãn khác nhau sẽ chuyển đại diện sang `review`.

**Riêng `percussion_filter.py` không dùng mô hình nhận diện nhạc cụ bằng âm thanh.** `accepted` là ứng viên đạt kiểm tra kỹ thuật + nhãn văn bản, không bảo đảm có đúng một nhạc cụ hay nhãn hoàn toàn đúng. Mỗi hàng có `single_instrument_verified=no` để không nhầm với dữ liệu đã được nghe xác minh. File tên `snare.wav` nhưng nội dung là guitar vẫn có thể lọt; cần nghe kiểm định trước khi dùng làm dữ liệu chuẩn cho báo cáo.

Một file có nhiều lần đánh cùng nhạc cụ vẫn có thể hợp đề. Tool không coi số lần đánh là số nhạc cụ, không tự tách file dãy nốt Iowa, và không đảm bảo loại được mọi bản phối nhiều nhạc cụ. Không dùng tool như bộ phát hiện nhiễu nền hay công cụ xác minh giấy phép.

MP3/WAV/AIFF/FLAC/OGG và các định dạng được libsndfile hỗ trợ có thể đọc trực tiếp. Tool cũng ghi nhận M4A/OPUS nhưng nếu bản libsndfile hiện tại không giải mã được, chúng vào `rejected.csv` với `decode_error` (không nhất thiết là file hỏng; cần đổi sang WAV bằng công cụ khác).

## Các nhãn

`kick`, `snare`, `hi_hat`, `tom`, `cymbal`, `marimba`, `xylophone`, `vibraphone`, `glockenspiel`, `crotales`, `timpani`, `gong`, `triangle`, `tambourine`, `woodblock`, `claves`, `castanets`, `cowbell`, `agogo`, `bongo`, `conga`, `djembe`, `cajon`, `tabla`, `shaker`, `maracas`, `cabasa`, `guiro`, `sleigh_bells`, `surdo`, `dunun`, `tenor_drum`, `vibraslap`, `ratchet`, `tubular_bells`.

Crash/ride/splash được gộp vào `cymbal`; open/closed hi-hat gộp vào `hi_hat`. Từ chung như `drum`, `percussion`, `bell`, `wood`, `clap` không tự động trở thành một lớp nhạc cụ. Với mục Bells của Iowa, nghe/đọc thông tin nguồn rồi dùng override phù hợp; không suy rằng mọi từ “bell” đều là glockenspiel. Từ viết tắt BD/SD/HH/WB có thể mơ hồ trong một số bộ, nên vẫn cần nghe kiểm định.

Muốn thêm từ khóa/nhãn, sửa bảng `ALIASES` ở đầu `percussion_filter.py`.

## Sửa nhãn thủ công

Sao chép `overrides_template.csv`, nghe các file gốc có trong `review.csv`, rồi sửa cột `label`. Dùng tên nhãn trong danh sách trên, `unknown` để tiếp tục chờ kiểm tra, hoặc `exclude` để loại. Ví dụ:

```csv
file,label
123.wav,snare
subfolder/456.wav,woodblock
789.wav,exclude
```

`file` phải khớp đường dẫn tương đối từ thư mục `--input` (cột `relative_path` của manifest). Không dùng đường dẫn file đã được đổi tên trong thư mục output. Nếu đường dẫn không tồn tại, tool dừng để tránh âm thầm bỏ qua nhãn sửa tay.

```sh
python percussion_filter.py \
  --input "data/one_shot_percussive_sounds" \
  --metadata "data/licenses.txt" \
  --overrides "manual_labels.csv" \
  --output "output/freesound-2"
```

Override chỉ thay nhãn; không bỏ qua các kiểm tra tín hiệu hoặc tự xác nhận chỉ có một nhạc cụ. Nếu cảnh báo chất lượng vẫn còn, mẫu vẫn nằm trong `review`.

Ví dụ thay ngưỡng với âm rất nhỏ/ngắn:

```sh
python percussion_filter.py --input "data/audio" --output "output/lan-2" \
  --min-duration 0.01 --min-active 0.005 --silence-db -85
```

## Kiểm tra tool

```sh
python -m unittest -v
```

Tests dùng âm tổng hợp để kiểm tra đường đi dữ liệu, kiểm tra tín hiệu, metadata, trùng file và an toàn sao chép. Đây **không phải** đánh giá độ chính xác nhận dạng trên dataset thật. Bộ tuyển chọn hiện có 655 tệp; số lượng và giới hạn kiểm chứng được ghi trong `filtered_output/README.md`.

Tài liệu thư viện đọc âm thanh: https://python-soundfile.readthedocs.io/en/latest/

## Đối chiếu nhãn bằng model âm thanh CLAP

`analyze_audio.py` đọc `manifest.csv` từ kết quả lọc và phân tích **audio thực tế** bằng `laion/clap-htsat-unfused`. Model không nhận tên file hoặc nhãn metadata làm đầu vào. Tool chỉ xuất báo cáo; không đổi nhãn, di chuyển, xóa hoặc sao chép lại audio.

Cài môi trường riêng (khuyến nghị Python 3.11):

```sh
python3.11 -m venv .venv-audio
.venv-audio/bin/python -m pip install -r requirements-model.txt
.venv-audio/bin/python analyze_audio.py \
  --input "/duong/dan/filtered_output" \
  --output "/duong/dan/filtered_output/clap_pilot"
```

Mặc định chọn ngẫu nhiên tối đa 25 file ở mỗi nhóm `(status, label)`, riêng `review/unknown` chọn 100 file; seed 42 để tái lập. Thêm `--full` để quét toàn bộ `accepted` và `review`. Folder báo cáo phải chưa tồn tại.

Lần đầu tải model khoảng 600 MB từ Hugging Face; audio được xử lý tại máy. Môi trường có PyTorch hỗ trợ sẽ tự chọn Apple MPS, CUDA hoặc CPU. Sau khi cache đủ model, có thể chạy offline bằng biến môi trường `HF_HUB_OFFLINE=1`. Phiên bản này xử lý đầy đủ các clip dài tối đa 10 giây, báo lỗi riêng nếu dài hơn, không tự cắt bỏ phần còn lại.

Đầu ra:

- `REPORT.md`: báo cáo tiếng Việt và mức đồng thuận theo từng nhãn.
- `predictions.csv`: nhãn top-3, điểm cosine, chênh lệch top-1/top-2 và thứ hạng nhãn cũ.
- `listen_first.csv`: các mẫu bất đồng hoặc chưa có nhãn, kèm đường dẫn audio để nghe lại.
- `label_summary.csv`, `summary.json`: thống kê.
- `predictions.jsonl`: top-5 và kết quả được ghi dần trong lúc chạy.
- `run_config.json`, `selected_files.csv`: model revision, phiên bản thư viện, prompts và danh sách đầu vào.

**Điểm cosine không phải xác suất, mức đồng thuận không phải độ chính xác.** Chưa có nhãn chuẩn được nghe xác minh, nên model không tự quyết định “valid” hoặc ghi đè nhãn. Các nhãn gần âm sắc (djembe/conga, castanets/woodblock…) có thể bị nhầm. Các nhóm ngoài nhạc cụ như `object_impact` hoặc `mixed_music` chỉ dùng để gợi ý kiểm tra, không phải bằng chứng chắc chắn để loại file.

Audio được chuyển mono, lấy mẫu lại 48 kHz theo đầu vào CLAP và lượng tử hóa int16. Bộ xử lý `repeatpad` lặp clip ngắn trong biểu diễn đầu vào 10 giây; audio gốc giữ nguyên. **Không dùng phép phân loại này để đếm số nhạc cụ hoặc chứng minh một file chỉ có một nhạc cụ.** Cần nghe một tập đánh giá độc lập, kiểm tra cả các mẫu mà model đồng ý với metadata, trước khi quyết định mức tự động hóa.
