#!/usr/bin/env python3
"""Phân tích bổ sung cho Mục 11 của báo cáo; chỉ đọc bảng đặc trưng đã có, không trích xuất lại.

- Tỷ số Q của riêng 5 thuộc tính thời gian và 16 thuộc tính phổ trong bộ A.
- Q của A, B, C khi chỉ giữ các tệp dài không quá 2 s (chuẩn hóa lại trên tập con đó).
- Khoảng cách trung bình trong từng lớp và khoảng cách giữa hai nhóm hi-hat ngắn/dài.
Kết quả ghi vào filtered_output/features/supplementary_analysis.json.
"""
import csv, json
from pathlib import Path
import numpy as np
from scipy.spatial.distance import pdist, cdist

ROOT = Path(__file__).resolve().parent.parent / 'filtered_output'


def load(name):
    with (ROOT / 'features' / name).open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    keys = [k for k in rows[0] if k not in ('sample_id', 'label')]
    return np.array([[float(r[k]) for k in keys] for r in rows]), np.array([r['label'] for r in rows]), [r['sample_id'] for r in rows]


def standardize(X):
    sd = X.std(axis=0)
    sd[sd < 1e-12] = 1
    return (X - X.mean(axis=0)) / sd


def ratio(X, labels):
    classes = sorted(set(labels))
    idx = {c: np.flatnonzero(labels == c) for c in classes}
    within = np.mean([pdist(X[idx[c]]).mean() for c in classes])
    between = np.mean([cdist(X[idx[c]], X[idx[d]]).mean() for i, c in enumerate(classes) for d in classes[i + 1:]])
    return dict(within_macro=float(within), between_macro=float(between), ratio=float(between / within))


def vectors(A, B):
    zA, zB = standardize(A), standardize(B)
    return {'A': zA / np.sqrt(21), 'B': zB / np.sqrt(39), 'C': np.c_[zA / np.sqrt(42), zB / np.sqrt(78)],
            'A_temporal5': zA[:, :5] / np.sqrt(5), 'A_spectral16': zA[:, 5:] / np.sqrt(16)}


def main():
    A, labels, ids = load('features_A.csv')
    B, labelsB, idsB = load('features_B.csv')
    assert ids == idsB and (labels == labelsB).all()
    with (ROOT / 'evidence/inventory.csv').open(encoding='utf-8-sig') as f:
        duration = {r['index']: float(r['duration_s']) for r in csv.DictReader(f)}
    short = np.array([duration[i] <= 2.0 for i in ids])
    full = vectors(A, B)
    sub = vectors(A[short], B[short])
    hh = labels == 'hi_hat'
    XA = full['A']
    result = {
        'files': len(ids), 'files_at_most_2s': int(short.sum()),
        'ratio_all_files': {k: ratio(X, labels) for k, X in full.items()},
        'ratio_at_most_2s_restandardized': {k: ratio(X, labels[short]) for k, X in sub.items()},
        'within_class_mean_distance': {k: {c: float(pdist(full[k][labels == c]).mean()) for c in sorted(set(labels))} for k in ('A', 'B')},
        'hi_hat_split_A': {'short_files': int((hh & short).sum()), 'long_files': int((hh & ~short).sum()),
                           'within_short': float(pdist(XA[hh & short]).mean()),
                           'within_long': float(pdist(XA[hh & ~short]).mean()),
                           'short_to_long': float(cdist(XA[hh & short], XA[hh & ~short]).mean())},
    }
    (ROOT / 'features/supplementary_analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
