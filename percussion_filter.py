#!/usr/bin/env python3
"""Conservative percussion dataset curation. Originals are never modified."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import soundfile as sf

EXTENSIONS = {'.wav', '.wave', '.aif', '.aiff', '.aifc', '.flac', '.ogg', '.mp3', '.au', '.opus', '.m4a'}
ALIASES = {
    'kick': ['kick', 'kickdrum', 'bass drum', 'bd'],
    'snare': ['snare', 'snaredrum', 'snare drum', 'sd'],
    'hi_hat': ['hi hat', 'hihat', 'hh', 'closedhat', 'openhat'],
    'tom': ['tom', 'toms', 'tomtom', 'tom tom', 'floor tom'],
    'cymbal': ['cymbal', 'cymbals', 'crash', 'ride', 'splash'],
    'marimba': ['marimba'], 'xylophone': ['xylophone'],
    'vibraphone': ['vibraphone', 'vibes'],
    'glockenspiel': ['glockenspiel', 'glock'], 'crotales': ['crotales', 'crotale'],
    'timpani': ['timpani', 'kettledrum'], 'gong': ['gong', 'gongs', 'tam tam', 'tamtam'],
    'triangle': ['triangle'], 'tambourine': ['tambourine', 'tambourines'],
    'woodblock': ['woodblock', 'woodblocks', 'wood block', 'wb'],
    'claves': ['clave', 'claves'], 'castanets': ['castanet', 'castanets'],
    'cowbell': ['cowbell', 'cow bell'], 'agogo': ['agogo'],
    'bongo': ['bongo', 'bongos'], 'conga': ['conga', 'congas', 'tumba'],
    'djembe': ['djembe'], 'cajon': ['cajon'], 'tabla': ['tabla'],
    'shaker': ['shaker', 'shakers'], 'maracas': ['maraca', 'maracas'],
    'cabasa': ['cabasa'], 'guiro': ['guiro'], 'sleigh_bells': ['sleigh bells', 'jingle bells'],
    'surdo': ['surdo'], 'dunun': ['dunun', 'djundjun', 'dun dun'],
    'tenor_drum': ['tenor drum'], 'vibraslap': ['vibraslap'],
    'ratchet': ['ratchet'], 'tubular_bells': ['tubular bells', 'tubular bell'],
}
FIELDS = ['source', 'relative_path', 'status', 'label', 'label_origin', 'evidence',
          'reasons', 'warnings', 'duration_s', 'sample_rate', 'channels', 'frames',
          'active_s', 'peak_dbfs', 'rms_dbfs', 'clipped_ratio', 'sha256', 'pcm_sha256',
          'duplicate_of', 'output', 'source_name', 'license', 'uploader', 'source_url',
          'single_instrument_verified']


def normalize(value):
    value = unicodedata.normalize('NFKD', str(value).lower().replace('đ', 'd'))
    value = ''.join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r'(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])', ' ', value)
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def has_phrase(text, phrase):
    return f' {normalize(phrase)} ' in f' {text} '


def guess_label(relative, record):
    # Usernames, descriptions and absolute ancestor paths are not label evidence.
    texts = [('path', str(relative.with_suffix('')))]
    for key in ('name', 'title', 'tags', 'instrument', 'label'):
        value = record.get(key)
        if value:
            texts.append((key, ' '.join(map(str, value)) if isinstance(value, list) else str(value)))
    matches, evidence = set(), []
    mixed = False
    for origin, raw in texts:
        text = normalize(raw)
        mixed |= any(has_phrase(text, p) for p in ('drum kit', 'drumkit', 'drum loop', 'drumloop', 'full kit', 'drum beat', 'drumbeat', 'drum set', 'drumset'))
        for label, aliases in ALIASES.items():
            hits = [a for a in aliases if has_phrase(text, a)]
            if hits:
                matches.add(label)
                evidence.append(f'{origin}:{label}({",".join(hits)})')
    label = next(iter(matches)) if len(matches) == 1 else ''
    reason = 'possible_drum_mixture' if mixed else ('ambiguous_labels' if len(matches) > 1 else ('unknown_label' if not matches else ''))
    return label, '; '.join(evidence), reason


def load_metadata(paths):
    """Freesound keyed JSON/list JSON, licenses.txt (JSON), or CSV."""
    index = {}
    def register(key, record):
        if not isinstance(record, dict):
            raise ValueError('Metadata records must be objects/dictionaries.')
        keys = [key, record.get('id'), record.get('sound_id'), record.get('freesound_id'),
                record.get('file'), record.get('filename'), record.get('path')]
        for k in keys:
            if k is not None and str(k):
                k = str(k)
                index[k] = {**index.get(k, {}), **record}
    for path in paths:
        with path.open(encoding='utf-8-sig', newline='') as f:
            if path.suffix.lower() == '.csv':
                for record in csv.DictReader(f):
                    register(None, record)
                continue
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get('results'), list):
            data = data['results']
        if isinstance(data, list):
            for record in data:
                register(None, record)
        elif isinstance(data, dict):
            for key, record in data.items():
                register(key, record)
        else:
            raise ValueError(f'Unsupported metadata structure: {path}')
    return index


def metadata_for(path, relative, index):
    record = {}
    # IDs work for <id>.wav and <id>_<username>__<name>.wav.
    ident = re.match(r'^(\d+)(?:_|$)', path.stem)
    keys = ([ident[1]] if ident else []) + [path.stem, path.name, relative.as_posix(), str(path)]
    for key in keys:
        record.update(index.get(key, {}))
    return record


def load_overrides(path):
    if not path:
        return {}
    result = {}
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not {'file', 'label'} <= set(reader.fieldnames or []):
            raise ValueError('Overrides CSV needs columns: file,label')
        for row in reader:
            label = row['label'].strip()
            if label not in ALIASES and label not in {'exclude', 'unknown'}:
                raise ValueError(f'Unknown override label: {label}')
            key = row['file'].strip().replace('\\', '/')
            if key in result:
                raise ValueError(f'Duplicate override: {key}')
            result[key] = label
    return result


def db(value):
    return round(20 * math.log10(max(float(value), 1e-12)), 3)


def inspect_audio(path, args):
    info = {}
    warnings, reasons = [], []
    raw_hash = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            raw_hash.update(block)
    info['sha256'] = raw_hash.hexdigest()
    try:
        with sf.SoundFile(path) as audio:
            sr, channels = audio.samplerate, audio.channels
            frames = 0
            energy, peak, clipped, nonfinite = 0., 0., 0, False
            window_rms = []
            pcm_hash = hashlib.sha256(f'{sr}:{channels}:'.encode())
            # Bound RAM independently of recording length; keep 10 ms RMS values.
            hop = max(1, round(sr * .01))
            for block in audio.blocks(blocksize=hop * 100, dtype='float32', always_2d=True):
                frames += len(block)
                if not np.isfinite(block).all():
                    nonfinite = True
                    break
                pcm_hash.update(np.asarray(block, dtype='<f4').tobytes())
                square = block.astype(np.float64) ** 2
                energy += float(square.sum())
                peak = max(peak, float(np.abs(block).max(initial=0)))
                clipped += int(np.count_nonzero(np.abs(block) >= .999))
                # Channel power, not channel averaging: opposite-phase stereo stays audible.
                mono_power = square.mean(axis=1)
                for start in range(0, len(block), hop):
                    part = mono_power[start:start + hop]
                    window_rms.append((math.sqrt(float(part.mean())), len(part)))
            if nonfinite:
                reasons.append('non_finite_samples')
            if not frames:
                reasons.append('empty_audio')
            duration = frames / sr
            rms = math.sqrt(energy / max(1, frames * channels))
            threshold = max(10 ** (args.silence_db / 20), peak * 10 ** (args.active_relative_db / 20))
            active = sum(n for value, n in window_rms if value > threshold) / sr
            ratio = clipped / max(1, frames * channels)
            info.update(duration_s=round(duration, 6), sample_rate=sr, channels=channels,
                        frames=frames, active_s=round(active, 6), peak_dbfs=db(peak),
                        rms_dbfs=db(rms), clipped_ratio=round(ratio, 6), pcm_sha256=pcm_hash.hexdigest())
            if not nonfinite and peak <= 10 ** (args.silence_db / 20):
                reasons.append('silent_or_near_silent')
            if duration < args.min_duration:
                reasons.append('too_short')
            if active < args.min_active:
                reasons.append('insufficient_active_audio')
            if ratio > args.max_clipped_ratio:
                warnings.append('possible_clipping')
            if sr < 16000:
                warnings.append('low_sample_rate')
            if frames and window_rms and peak > 0 and window_rms[-1][0] > peak * .3:
                warnings.append('strong_audio_at_end')
    except (sf.SoundFileError, ValueError, OverflowError) as exc:
        reasons.append('decode_error: ' + str(exc))
    return info, reasons, warnings


def write_csv(path, rows, fields=FIELDS):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def run(args):
    source, output = args.input.resolve(), args.output.resolve()
    if not source.is_dir():
        raise ValueError(f'Input directory not found: {source}')
    if output == source or source.is_relative_to(output):
        raise ValueError('Output cannot be the input directory or its ancestor.')
    if output.exists():
        raise ValueError('Output already exists. Choose a NEW folder to avoid stale files or overwrites.')
    metadata = load_metadata(args.metadata)
    overrides = load_overrides(args.overrides)
    files = sorted(p for p in source.rglob('*') if p.is_file() and not p.is_symlink()
                   and p.suffix.lower() in EXTENSIONS and not p.is_relative_to(output)
                   and '__MACOSX' not in p.parts and not p.name.startswith('._'))
    if not files:
        raise ValueError('No audio files found. Extract the downloaded ZIP first.')
    rows = []
    used_overrides = set()
    for number, path in enumerate(files, 1):
        relative = path.relative_to(source)
        record = metadata_for(path, relative, metadata)
        label, evidence, label_reason = guess_label(relative, record)
        origin = 'metadata_or_filename_rule'
        override = overrides.get(relative.as_posix())
        if override:
            used_overrides.add(relative.as_posix())
            label = override if override in ALIASES else ''
            label_reason = 'manual_exclude' if override == 'exclude' else ('unknown_label' if override == 'unknown' else '')
            origin, evidence = 'manual_override', override
        try:
            info, reasons, warnings = inspect_audio(path, args)
        except OSError as exc:
            info, reasons, warnings = {}, ['read_error: ' + str(exc)], []
        if label_reason == 'manual_exclude':
            reasons.append(label_reason)
        if reasons:
            status = 'rejected'
        elif label_reason or warnings:
            status = 'review'
        else:
            status = 'accepted'
        rows.append(dict(source=str(path), relative_path=relative.as_posix(), status=status,
                         label=label, label_origin=origin, evidence=evidence,
                         reasons='; '.join(reasons + ([label_reason] if label_reason and label_reason not in reasons else [])),
                         warnings='; '.join(warnings), **info,
                         source_name=record.get('name', ''), license=record.get('license', ''),
                         uploader=record.get('username', record.get('uploader', '')),
                         source_url=record.get('url', ''), single_instrument_verified='no'))
        if number % 100 == 0 or number == len(files):
            print(f'Checked {number}/{len(files)}', file=sys.stderr)
    unknown_overrides = set(overrides) - used_overrides
    if unknown_overrides:
        raise ValueError('Override paths not found (use paths relative to input): ' + ', '.join(sorted(unknown_overrides)))
    # Pick a well-labelled, quality-passing representative first, independently of file order.
    seen_raw, seen_pcm = {}, {}
    rank = {'accepted': 0, 'review': 1, 'rejected': 2}
    for row in sorted(rows, key=lambda r: (rank[r['status']], r['relative_path'])):
        if row['status'] == 'rejected':
            continue
        raw, pcm = row.get('sha256'), row.get('pcm_sha256')
        previous = seen_raw.get(raw) or seen_pcm.get(pcm)
        if previous:
            row.update(status='duplicate', duplicate_of=previous['relative_path'])
            if row['label'] and previous['label'] and row['label'] != previous['label']:
                previous['status'] = 'review'
                previous['warnings'] = '; '.join(filter(None, [previous['warnings'], 'duplicate_label_conflict']))
                row['warnings'] = '; '.join(filter(None, [row['warnings'], 'duplicate_label_conflict']))
        else:
            if raw:
                seen_raw[raw] = row
            if pcm:
                seen_pcm[pcm] = row
    output.mkdir(parents=True)
    for row in rows:
        if row['status'] not in {'accepted', 'review'}:
            continue
        path = Path(row['source'])
        # Hash relative path as well: equal stems from different packs never overwrite.
        identity = hashlib.sha256(row['relative_path'].encode()).hexdigest()[:12]
        destination = output / row['status'] / (row['label'] or 'unknown') / f'{identity}__{path.name}'
        row['output'] = str(destination)
        if not args.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(path, destination)
            except OSError as exc:
                row['status'] = 'copy_error'
                row['reasons'] += '; copy_error: ' + str(exc)
                if destination.exists():
                    destination.unlink()
    write_csv(output / 'manifest.csv', rows)
    for status in ('accepted', 'review', 'rejected', 'duplicate', 'copy_error'):
        write_csv(output / f'{status}.csv', [r for r in rows if r['status'] == status])
    write_csv(output / 'overrides_template.csv',
              [{'file': r['relative_path'], 'label': r['label'] or 'unknown'} for r in rows if r['status'] == 'review'],
              ['file', 'label'])
    summary = {'input': str(source), 'output': str(output), 'dry_run': args.dry_run,
               'total_audio_files': len(rows), 'status_counts': dict(Counter(r['status'] for r in rows)),
               'accepted_by_label': dict(sorted(Counter(r['label'] for r in rows if r['status'] == 'accepted').items())),
               'accepted_at_least_500': sum(r['status'] == 'accepted' for r in rows) >= 500,
               'note': 'Accepted means signal checks + unambiguous text label; not acoustic verification of one instrument.',
               'config': {k: str(v) if isinstance(v, Path) else [str(p) for p in v] if isinstance(v, list) else v
                          for k, v in vars(args).items()}}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if any(r['status'] == 'copy_error' for r in rows) else 0


def parser():
    p = argparse.ArgumentParser(description='Filter percussion audio and copy into instrument folders; original files are untouched.')
    p.add_argument('--input', type=Path, required=True, help='Extracted audio directory (recursive)')
    p.add_argument('--output', type=Path, required=True, help='New output directory')
    p.add_argument('--metadata', type=Path, action='append', default=[], help='Freesound JSON/licenses.txt or CSV; repeatable')
    p.add_argument('--overrides', type=Path, help='Manual CSV: file,label (relative file path)')
    p.add_argument('--dry-run', action='store_true', help='Write reports only, do not copy audio')
    p.add_argument('--min-duration', type=float, default=.02, help='Minimum total seconds (default .02, not 1 second)')
    p.add_argument('--min-active', type=float, default=.01, help='Minimum active seconds, estimated on 10 ms windows')
    p.add_argument('--silence-db', type=float, default=-70, help='Absolute silence threshold dBFS')
    p.add_argument('--active-relative-db', type=float, default=-40, help='Activity threshold relative to peak')
    p.add_argument('--max-clipped-ratio', type=float, default=.01, help='Above this near-full-scale fraction: manual review')
    return p


def main():
    p = parser()
    args = p.parse_args()
    if not all(math.isfinite(v) for v in [args.min_duration, args.min_active, args.silence_db, args.active_relative_db, args.max_clipped_ratio]):
        p.error('Thresholds must be finite.')
    if args.min_duration < 0 or args.min_active < 0 or not 0 <= args.max_clipped_ratio <= 1:
        p.error('Durations must be nonnegative and clipped ratio must be in [0, 1].')
    if args.silence_db >= 0 or args.active_relative_db >= 0:
        p.error('dB thresholds must be negative.')
    try:
        return run(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
