#!/usr/bin/env python3
"""Chép các tệp truy vấn thử (không thuộc kho 655 tệp) từ bản tải Freesound One-Shot Percussive Sounds.

  ngoai_kho/<nhãn>/  mọi tệp có nhãn metadata là nhạc cụ ngoài 13 lớp của kho (Yêu cầu 4: nhạc cụ chưa có);
  trong_lop/<nhãn>/  mỗi lớp đã có một tệp mới: mô hình CLAP đồng thuận nhãn metadata, điểm cosine cao nhất,
                     không trùng PCM hay tên gốc với tệp nào trong kho.
Tệp không đạt điều kiện Mục 2 vẫn được chép (để minh họa truy vấn bị từ chối), cột dat_muc_2 ghi kết quả.
Nhãn lấy theo metadata Freesound, chưa được nghe kiểm tra; cột nhan_trong_clap_top3 ghi nhãn đó có nằm trong 3 nhãn
mô hình CLAP gợi ý từ chính âm thanh hay không (chỉ là đối chiếu tự động).
Chạy một lần:  python csdl_tim_kiem/chuan_bi_truy_van_thu.py [thư mục bản tải Freesound]
"""
import csv
import shutil
import sys
from pathlib import Path

from dac_trung import REPO, LoiAmThanh, doc_am_thanh, ma_bam_pcm

NGUON = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / 'Downloads/one_shot_percussive_sounds')
DU_DOAN = REPO / 'output/dataset_archive_2026-10-20/before_selection/clap_full_2026-10-14/predictions.csv'
RA = Path(__file__).resolve().parent / 'truy_van_thu'


def main():
    kho = list(csv.DictReader((REPO / 'filtered_output/accepted.csv').open(encoding='utf-8-sig')))
    lop, bam, ten = {r['label'] for r in kho}, {r['pcm_sha256'] for r in kho}, {r['source_name'] for r in kho}
    hang = [r for r in csv.DictReader(DU_DOAN.open(encoding='utf-8-sig')) if r['original_status'] == 'accepted']
    chon = [('ngoai_kho', r) for r in hang if r['original_label'] not in lop]
    for c in sorted(lop):
        ung_vien = sorted((r for r in hang if r['original_label'] == c and r['comparison'] == 'agrees_with_metadata'
                           and r['source_name'] not in ten), key=lambda r: -float(r['top1_cosine']))
        for r in ung_vien:
            try:
                y, _ = doc_am_thanh(NGUON / r['relative_path'])
            except LoiAmThanh:
                continue
            if ma_bam_pcm(y) not in bam:
                chon.append(('trong_lop', r))
                break
    if RA.exists():
        shutil.rmtree(RA)
    dong = []
    for nhom, r in chon:
        goc = NGUON / r['relative_path']
        dich = RA / nhom / r['original_label'] / f'fs{goc.stem}.wav'
        dich.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(goc, dich)
        try:
            y, _ = doc_am_thanh(dich)
            dat, trung = 'co', ma_bam_pcm(y) in bam
        except LoiAmThanh as e:
            dat, trung = str(e), False
        assert not trung, dich
        top3 = [r['top1_label'], r['top2_label'], r['top3_label']]  # đối chiếu tự động bằng CLAP, chưa phải nghe
        dong.append(dict(nhom=nhom, duong_dan=dich.relative_to(RA).as_posix(), nhan_metadata=r['original_label'],
                         ma_freesound=goc.stem, ten_goc=r['source_name'], dat_muc_2=dat,
                         clap_top3=' / '.join(top3), nhan_trong_clap_top3='co' if r['original_label'] in top3 else 'khong'))
    with (RA / 'danh_sach.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(dong[0]))
        w.writeheader()
        w.writerows(dong)
    print(f'{len(dong)} tệp; ngoài kho {sum(d["nhom"] == "ngoai_kho" for d in dong)}, '
          f'không đạt Mục 2 {sum(d["dat_muc_2"] != "co" for d in dong)}')


if __name__ == '__main__':
    main()
