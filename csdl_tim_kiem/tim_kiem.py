#!/usr/bin/env python3
"""Yêu cầu 4: tìm 5 tệp trong kho giống nhất với một tệp âm thanh nhạc cụ gõ.

Ví dụ:  python csdl_tim_kiem/tim_kiem.py duong/dan/tieng_trong.wav --bo A
"""
import argparse
import json
import sys

from csdl import BO_MAC_DINH, CSDL, DB_MAC_DINH
from dac_trung import LoiAmThanh


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tep', help='tệp truy vấn (WAV, FLAC, OGG, AIFF, MP3...), số kênh và tần số lấy mẫu bất kỳ')
    ap.add_argument('--bo', choices='ABC', default=BO_MAC_DINH, help='bộ đặc trưng (mặc định %(default)s)')
    ap.add_argument('-k', type=int, default=5, help='số kết quả (mặc định 5)')
    ap.add_argument('--db', default=DB_MAC_DINH)
    ap.add_argument('--vet-can', action='store_true', help='tìm tuần tự thay vì dùng cây k-d')
    ap.add_argument('--json', action='store_true', help='in kết quả dạng JSON')
    args = ap.parse_args()
    try:
        kq = CSDL(args.db).tim_kiem(args.tep, args.bo, args.k, args.vet_can)
    except LoiAmThanh as e:
        sys.exit(f'Từ chối truy vấn: {e}')
    if args.json:
        bo_di = {'u', 'a', 'b'}
        print(json.dumps({k: v for k, v in kq.items() if k not in bo_di}, ensure_ascii=False, indent=2))
        return
    print(f'Truy vấn: {args.tep} ({kq["thoi_luong_s"]:.2f} s), bộ {kq["bo"]}, '
          f'{kq["so_phep_tinh_khoang_cach"]} phép tính khoảng cách')
    if kq['trung_tep_trong_kho']:
        print(f'  Tệp này đã có trong kho (mã {kq["trung_tep_trong_kho"]}), bỏ khỏi kết quả.')
    for r in kq['ket_qua']:
        print(f'{r["hang"]}. {r["nhan"]:<11} d={r["khoang_cach"]:.3f}  s={r["do_tuong_dong"]:.3f}  '
              f'{r["duong_dan"]}  [{r["nguon"]}]')
        g = ', '.join(t for t, _ in r['giai_thich']['giong'])
        k = ', '.join(f'{t} ({dz:.1f}σ)' for t, dz in r['giai_thich']['khac'])
        print(f'     giống nhất: {g}\n     khác nhất: {k}')


if __name__ == '__main__':
    main()
