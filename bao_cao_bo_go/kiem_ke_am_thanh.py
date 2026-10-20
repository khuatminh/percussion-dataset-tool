#!/usr/bin/env python3
"""Read-only audit of accepted audio. Writes evidence, never changes recordings."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import soundfile as sf
from scipy import signal


def csv_write(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True, help='filtered_output directory')
    p.add_argument('--out', type=Path, default=Path(__file__).parent / 'evidence')
    a = p.parse_args()
    root, out = a.root.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source_rows = list(csv.DictReader((root / 'accepted.csv').open(encoding='utf-8-sig')))
    def audio_path(row):
        path = Path(row['output'])
        return (path if path.is_absolute() else root / path).resolve()
    metadata = {str(audio_path(r)): r for r in source_rows}
    extensions = {'.wav', '.flac', '.aif', '.aiff', '.ogg', '.mp3', '.m4a', '.opus'}
    paths = sorted(p for p in (root / 'accepted').rglob('*')
                   if p.is_file() and p.suffix.lower() in extensions and not p.name.startswith('.'))
    rows, groups, errors = [], defaultdict(list), []
    for i, path in enumerate(paths, 1):
        meta = metadata.get(str(path), {})
        try:
            info = sf.info(path)
            x, sr = sf.read(path, dtype='float32', always_2d=True)
            if not len(x) or not np.isfinite(x).all():
                raise ValueError('empty or non-finite audio')
            energy = np.mean(x.astype(np.float64) ** 2, axis=1)
            peak = float(np.max(np.abs(x)))
            rms = float(np.sqrt(energy.mean()))
            hop = max(1, round(sr * .01))
            chunks = [(float(np.sqrt(energy[j:j+hop].mean())), len(energy[j:j+hop]))
                      for j in range(0, len(x), hop)]
            threshold = max(10 ** (-70/20), peak * .01)
            active = sum(n for r, n in chunks if r > threshold) / sr
            # Energy support: interval containing the middle 90% of total energy.
            cumulative = np.cumsum(energy)
            t05, t95 = [int(np.searchsorted(cumulative, cumulative[-1] * q)) / sr
                        for q in (.05, .95)]
            # Power spectrum averaged over channels avoids stereo cancellation.
            frame = min(len(x), round(.025 * sr))
            step = min(frame, round(.010 * sr))
            freqs, times, z = signal.stft(x.T, fs=sr, window='hann', nperseg=frame,
                                         noverlap=frame-step, nfft=512 if sr == 16000 else max(512, frame),
                                         boundary=None, padded=False, axis=-1)
            power = np.mean(np.abs(z) ** 2, axis=0).astype(np.float64)
            spectrum = power.sum(axis=1)
            centroid = float((freqs * spectrum).sum() / max(spectrum.sum(), 1e-30))
            low_ratio = float(spectrum[freqs < 500].sum() / max(spectrum.sum(), 1e-30))
            dominant = x[:, int(np.argmax(np.mean(x.astype(np.float64)**2, axis=0)))]
            mask = np.repeat([r > threshold for r, n in chunks], hop)[:len(x)]
            valid_pairs = mask[1:] & mask[:-1]
            zcr = float(np.mean((np.signbit(dominant[1:]) != np.signbit(dominant[:-1]))[valid_pairs])) if valid_pairs.any() else 0.
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            pcm = hashlib.sha256(f'{sr}:{x.shape[1]}:'.encode() + np.asarray(x, dtype='<f4').tobytes()).hexdigest()
            flags = []
            if peak <= 10**(-70/20): flags.append('silent_or_near_silent')
            if len(x)/sr < .02: flags.append('too_short')
            if active < .01: flags.append('insufficient_active_audio')
            clipped = float(np.mean(np.abs(x) >= .999))
            if clipped > .01: flags.append('possible_clipping')
            if chunks[-1][0] > .3*peak: flags.append('strong_audio_at_end')
            if sr < 16000: flags.append('low_sample_rate')
            row = dict(index=i, relative_path=path.relative_to(root).as_posix(), label=path.parent.name,
                       bytes=path.stat().st_size, format=info.format, subtype=info.subtype,
                       sample_rate=sr, channels=x.shape[1], frames=len(x), duration_s=len(x)/sr,
                       active_s=active, energy90_s=t95-t05, peak_dbfs=20*np.log10(max(peak, 1e-12)),
                       rms_dbfs=20*np.log10(max(rms, 1e-12)), clipped_ratio=clipped,
                       spectral_centroid_power_hz=centroid, energy_below_500hz=low_ratio, active_zcr=zcr,
                       sha256=sha, pcm_sha256=pcm, in_accepted_csv=bool(meta),
                       label_matches_csv=meta.get('label') == path.parent.name,
                       sha_matches_csv=meta.get('sha256') == sha,
                       pcm_matches_csv=meta.get('pcm_sha256') == pcm,
                       source_relative_path=meta.get('relative_path',''), source_name=meta.get('source_name',''),
                       uploader=meta.get('uploader',''), source_url=meta.get('source_url',''),
                       license=meta.get('license',''), single_instrument_verified=meta.get('single_instrument_verified',''),
                       audit_flags=';'.join(flags))
            rows.append(row)
            groups[row['label']].append(row)
        except Exception as exc:
            errors.append(dict(path=str(path), error=str(exc)))
    if not rows:
        raise RuntimeError('No decodable audio')
    csv_write(out/'inventory.csv', rows)
    stats = []
    for label, rs in sorted(groups.items()):
        durations = [r['duration_s'] for r in rs]
        stats.append(dict(label=label, count=len(rs), duration_min_s=min(durations),
                          duration_median_s=float(np.median(durations)), duration_max_s=max(durations),
                          duration_total_s=sum(durations),
                          active_median_s=float(np.median([r['active_s'] for r in rs])),
                          energy90_median_s=float(np.median([r['energy90_s'] for r in rs])),
                          centroid_median_hz=float(np.median([r['spectral_centroid_power_hz'] for r in rs])),
                          low_energy_median=float(np.median([r['energy_below_500hz'] for r in rs])),
                          zcr_median=float(np.median([r['active_zcr'] for r in rs]))))
    csv_write(out/'class_statistics.csv', stats)
    duplicate_groups = {}
    for key in ['sha256', 'pcm_sha256']:
        ids = defaultdict(list)
        for r in rows: ids[r[key]].append(r['relative_path'])
        duplicate_groups[key] = {k:v for k,v in ids.items() if len(v)>1}
    physical = {str(p) for p in paths}
    summary = dict(audit_time=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(), root=str(root),
                   files_on_disk=len(paths), decoded_files=len(rows), classes=len(groups),
                   counts={s['label']:s['count'] for s in stats}, csv_rows=len(source_rows),
                   missing_csv_paths=[r['output'] for r in source_rows if str(audio_path(r)) not in physical],
                   unique_file_sha256=len({r['sha256'] for r in rows}),
                   unique_pcm_sha256=len({r['pcm_sha256'] for r in rows}),
                   metadata_checks={k:sum(bool(r[k]) for r in rows) for k in ['in_accepted_csv','label_matches_csv','sha_matches_csv','pcm_matches_csv']},
                   formats=dict(Counter(r['format'] for r in rows)), subtypes=dict(Counter(r['subtype'] for r in rows)),
                   sample_rates=dict(Counter(r['sample_rate'] for r in rows)), channels=dict(Counter(r['channels'] for r in rows)),
                   duration_min_s=min(r['duration_s'] for r in rows), duration_max_s=max(r['duration_s'] for r in rows),
                   duration_median_s=float(np.median([r['duration_s'] for r in rows])),
                   duration_total_s=sum(r['duration_s'] for r in rows), total_bytes=sum(r['bytes'] for r in rows),
                   duration_under_0_1_s=sum(r['duration_s'] < .1 for r in rows),
                   duration_at_most_1_s=sum(r['duration_s'] <= 1 for r in rows),
                   peak_dbfs_min=min(r['peak_dbfs'] for r in rows), peak_dbfs_max=max(r['peak_dbfs'] for r in rows),
                   flags=dict(Counter(flag for r in rows for flag in r['audit_flags'].split(';') if flag)),
                   verified=dict(Counter(r['single_instrument_verified'] for r in rows)),
                   licenses=dict(Counter(r['license'] for r in rows)),
                   source_groups=dict(Counter(r['source_relative_path'].split('/')[0] for r in rows)),
                   duplicate_groups=duplicate_groups, errors=errors,
                   numpy_version=np.__version__, soundfile_version=sf.__version__)
    (out/'audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    flagged = [r for r in rows if r['audit_flags']]
    if flagged: csv_write(out/'flagged_files.csv', flagged)
    short = [r for r in rows if r['duration_s'] < .1]
    if short: csv_write(out/'short_files_under_100ms.csv', short)
    (out/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['relative_path']}\n" for r in rows),encoding='utf-8')
    # Balanced deterministic illustrations: closest to class medians in duration and centroid.
    reps = []
    for s in stats:
        rs=groups[s['label']]
        rep=min(rs,key=lambda r:abs(np.log(max(r['duration_s'],1e-9)/s['duration_median_s']))+abs(np.log(max(r['spectral_centroid_power_hz'],1e-9)/s['centroid_median_hz'])))
        reps.append(rep)
    csv_write(out/'representative_files.csv', reps)
    review = [dict(relative_path=r['relative_path'],label=r['label'],reviewer='',review_date='',
                   single_instrument='',attack_and_decay_sufficient='',label_correct='',notes='') for r in rows]
    csv_write(out/'listening_checklist.csv', review)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
