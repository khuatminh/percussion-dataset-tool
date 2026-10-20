#!/usr/bin/env python3
"""Read-only CLAP audit of percussion_filter output; predictions are not ground truth."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


INSTRUMENTS = {
    'kick': 'a bass drum or kick drum',
    'snare': 'a snare drum',
    'hi_hat': 'a hi-hat cymbal',
    'tom': 'a tom-tom drum',
    'cymbal': 'a crash, ride or splash cymbal',
    'marimba': 'a marimba', 'xylophone': 'a xylophone',
    'vibraphone': 'a vibraphone', 'glockenspiel': 'a glockenspiel',
    'crotales': 'crotales, small tuned metal cymbals',
    'timpani': 'timpani kettle drums', 'gong': 'a gong or tam-tam',
    'triangle': 'a triangle percussion instrument',
    'tambourine': 'a tambourine', 'woodblock': 'a woodblock percussion instrument',
    'claves': 'claves, two wooden percussion sticks', 'castanets': 'castanets',
    'cowbell': 'a cowbell percussion instrument', 'agogo': 'agogo bells',
    'bongo': 'bongo drums', 'conga': 'a conga drum', 'djembe': 'a djembe drum',
    'cajon': 'a cajon box drum', 'tabla': 'tabla drums',
    'shaker': 'a percussion shaker', 'maracas': 'maracas',
    'cabasa': 'a cabasa percussion instrument', 'guiro': 'a guiro being scraped',
    'sleigh_bells': 'sleigh bells jingling', 'surdo': 'a surdo drum',
    'dunun': 'a dunun African bass drum', 'tenor_drum': 'a tenor drum',
    'vibraslap': 'a vibraslap', 'ratchet': 'a ratchet percussion instrument',
    'tubular_bells': 'tubular bells',
}
OTHER_SOUNDS = {
    'speech': 'a person speaking', 'singing': 'a person singing',
    'mixed_music': 'a full music track with several instruments playing together',
    'drum_kit': 'a drum kit with kick, snare and cymbals playing together',
    'hand_clap': 'hands clapping', 'finger_snap': 'fingers snapping',
    'object_impact': 'an everyday object hitting a surface',
    'door_knock': 'someone knocking on a door',
    'electronic_effect': 'a synthetic laser or video game sound effect',
    'noise': 'static noise or hissing', 'guitar': 'a guitar being played',
    'piano': 'a piano being played', 'bell': 'an ordinary doorbell or church bell ringing',
}
DEFAULT_MODEL = 'laion/clap-htsat-unfused'
DEFAULT_REVISION = '8fa0f1c6d0433df6e97c127f64b2a1d6c0dcda8a'


def select_rows(root, per_group, unknown_limit, seed, full=False):
    with (root / 'manifest.csv').open(encoding='utf-8-sig', newline='') as f:
        manifest = list(csv.DictReader(f))
    groups = defaultdict(list)
    for row in manifest:
        if row['status'] in {'accepted', 'review'}:
            groups[(row['status'], row['label'] or 'unknown')].append(row)
    rng = random.Random(seed)
    selected = []
    for key in sorted(groups):
        candidates = sorted(groups[key], key=lambda r: r['relative_path'])
        limit = unknown_limit if key == ('review', 'unknown') else per_group
        selected.extend(candidates if full else rng.sample(candidates, min(limit, len(candidates))))
    return selected, manifest


def load_audio(path):
    x, sr = sf.read(path, dtype='float32', always_2d=True)
    if not len(x) or not np.isfinite(x).all():
        raise ValueError('Empty or nonfinite audio')
    duration = len(x) / sr
    if duration > 10:
        raise ValueError('Pilot supports complete clips up to 10 seconds; no silent cropping')
    mono = x.mean(axis=1)
    power = np.mean(x.astype(np.float64) ** 2, axis=0)
    if np.mean(mono.astype(np.float64) ** 2) < .1 * power.max():
        mono = x[:, int(power.argmax())]
    if sr != 48000:
        divisor = math.gcd(sr, 48000)
        mono = resample_poly(mono, 48000 // divisor, sr // divisor)
    # Match the original model's audio quantization; no gain normalization.
    mono = (np.clip(mono, -1, 1) * 32767).astype(np.int16).astype(np.float32) / 32767
    return mono, duration


def csv_write(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows, manifest, output, config):
    ok = [r for r in rows if not r.get('error')]
    accepted = [r for r in ok if r['original_status'] == 'accepted']
    counts = Counter(r['comparison'] for r in ok)
    by_label = []
    for label in sorted({r['original_label'] for r in accepted}):
        subset = [r for r in accepted if r['original_label'] == label]
        by_label.append(dict(label=label, sampled=len(subset),
                             top1_agrees=sum(r['top1_label'] == label for r in subset),
                             original_in_top3=sum(r['original_rank'] <= 3 for r in subset),
                             model_top1_counts=dict(Counter(r['top1_label'] for r in subset))))
    summary = dict(model=config['model'], revision=config['revision'],
                   analyzed=len(rows), successful=len(ok), errors=len(rows)-len(ok),
                   inventory_counts=dict(Counter(r['status'] for r in manifest)),
                   comparisons=dict(counts), accepted_sampled=len(accepted),
                   accepted_top1_agrees=sum(r['top1_label'] == r['original_label'] for r in accepted),
                   accepted_original_in_top3=sum(r['original_rank'] <= 3 for r in accepted),
                   accepted_by_label=by_label,
                   unknown_suggestions=dict(Counter(r['top1_label'] for r in ok if not r['original_label'])),
                   notes=['Cosine similarities and margins are not probabilities.',
                          'Agreement with metadata is not accuracy; metadata can be wrong.',
                          ('Full accepted/review scan.' if config['full'] else 'Stratified sampling does not estimate population agreement without weighting.'),
                          'No single-instrument or noise-free guarantee. No files relabelled or moved.',
                          'Default repeatpad preprocessing repeats short clips internally to 10 seconds; original files unchanged.',
                          'Short sounds are out-of-domain relative to many CLAP training clips; inspect manually.'])
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    fields = ['relative_path', 'audio_path', 'original_status', 'original_label', 'source_name',
              'top1_label', 'top1_cosine', 'top2_label', 'top2_cosine', 'top3_label', 'top3_cosine',
              'top1_top2_margin', 'original_rank', 'original_cosine', 'comparison', 'duration_s',
              'single_instrument_verified', 'error']
    csv_write(output / 'predictions.csv', rows, fields)
    flagged = sorted([r for r in ok if r['comparison'] != 'agrees_with_metadata'],
                     key=lambda r: (r['original_status'] != 'accepted', -r['top1_top2_margin']))
    csv_write(output / 'listen_first.csv', flagged, fields)
    csv_write(output / 'label_summary.csv', by_label, ['label', 'sampled', 'top1_agrees', 'original_in_top3', 'model_top1_counts'])
    lines = ['# Thử nghiệm phân tích âm thanh bằng CLAP', '',
             f"- Model: `{config['model']}`; revision `{config['revision']}`.",
             f"- Chế độ: {'toàn bộ accepted/review' if config['full'] else 'lấy mẫu phân tầng theo trạng thái và nhãn'}, seed {config['seed']}.",
             f"- Đã xử lý: {len(rows)} file; thành công {len(ok)}; lỗi {len(rows)-len(ok)}.",
             f"- Nhóm accepted trong mẫu: {len(accepted)} file; top-1 trùng metadata: {summary['accepted_top1_agrees']}; nhãn metadata nằm trong top-3: {summary['accepted_original_in_top3']}.",
             '- Đây là mức đồng thuận với nhãn cũ, **không phải độ chính xác**. Chưa có nhãn chuẩn được nghe xác minh.',
             '- Model chỉ thấy audio, không thấy tên file, metadata hay nhãn thư mục.',
             '- Điểm cosine không phải xác suất; không áp dụng ngưỡng chấp nhận tự động khi chưa hiệu chỉnh.',
             '- Không khẳng định chỉ có một nhạc cụ. Giữ nguyên toàn bộ file và nhãn gốc.',
             ('- Quét toàn bộ file accepted/review trong manifest.' if config['full'] else '- Thử nghiệm theo lớp không đại diện theo tỷ lệ số lượng của toàn bộ dataset.'),
             '', '| Nhãn metadata | Số mẫu | Top-1 trùng | Nhãn cũ trong top-3 |',
             '|---|---:|---:|---:|']
    lines += [f"| {r['label']} | {r['sampled']} | {r['top1_agrees']} | {r['original_in_top3']} |" for r in by_label]
    lines += ['', '## Cách sử dụng kết quả', '',
              'Mở `listen_first.csv` để ưu tiên nghe mẫu bất đồng và mẫu chưa có nhãn. `audio_path` là đường dẫn để nghe lại. Các gợi ý ngoài bộ gõ chỉ là nghi vấn, không tự động loại file.',
              'Mở `predictions.csv` để xem top-3, chênh lệch điểm và thứ hạng nhãn cũ. `predictions.jsonl` lưu top-5 và bằng chứng đầy đủ.',
              'Với mẫu một giây, processor repeatpad lặp âm thanh trong biểu diễn đầu vào. Đây không phải bằng chứng file gốc có nhiều lần gõ; không dùng đầu ra để đếm nhạc cụ.',
              '', 'Model: https://huggingface.co/laion/clap-htsat-unfused',
              'Tài liệu: https://huggingface.co/docs/transformers/v4.57.1/en/model_doc/clap', '']
    (output / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--per-group', default=25, type=int)
    parser.add_argument('--unknown-limit', default=100, type=int)
    parser.add_argument('--seed', default=42, type=int)
    parser.add_argument('--batch-size', default=8, type=int)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--device', default='auto', choices=['auto', 'cpu', 'mps', 'cuda'])
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--revision', default=DEFAULT_REVISION)
    args = parser.parse_args()
    if min(args.per_group, args.unknown_limit, args.batch_size) <= 0:
        parser.error('Sampling limits and batch size must be positive')
    root, output = args.input.resolve(), args.output.resolve()
    if output.exists():
        parser.error('Output already exists: choose a new report folder')
    selected, manifest = select_rows(root, args.per_group, args.unknown_limit, args.seed, args.full)
    if not selected:
        parser.error('No accepted/review records in manifest')
    print(f'Selected {len(selected)} files.', flush=True)
    import torch
    import transformers
    from transformers import ClapModel, ClapProcessor
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = args.device
    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
    print(f'Loading CLAP on {device}...', flush=True)
    processor = ClapProcessor.from_pretrained(args.model, revision=args.revision)
    # This pinned official checkpoint ships PyTorch weights. weights_only prevents
    # arbitrary pickle execution; explicitly avoid background format conversion.
    model = ClapModel.from_pretrained(args.model, revision=args.revision, weights_only=True,
                                     use_safetensors=False).to(device).eval()
    descriptions = {**INSTRUMENTS, **OTHER_SOUNDS}
    labels = list(descriptions)
    templates = ['The sound of {}.', 'An audio recording of {}.', 'This is the sound of {}.']
    prompts = [t.format(descriptions[label]) for label in labels for t in templates]
    tokens = processor.tokenizer(prompts, padding=True, return_tensors='pt').to(device)
    with torch.inference_mode():
        text_features = model.get_text_features(**tokens)
        text_features = torch.nn.functional.normalize(text_features, dim=-1)
        text_features = torch.nn.functional.normalize(text_features.reshape(len(labels), len(templates), -1).mean(dim=1), dim=-1)
    output.mkdir(parents=True)
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    config.update(device=device, torch_version=torch.__version__, transformers_version=transformers.__version__,
                  labels=descriptions, prompts=prompts, selected=len(selected),
                  manifest_sha256=hashlib.sha256((root / 'manifest.csv').read_bytes()).hexdigest(),
                  preprocessing='whole clip <=10s; mono; resample_poly to 48kHz; int16 quantize; repeatpad to 10s')
    (output / 'run_config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    csv_write(output / 'selected_files.csv', selected, list(selected[0]))
    rows = []
    started = time.monotonic()
    with (output / 'predictions.jsonl').open('w', encoding='utf-8') as log:
        for offset in range(0, len(selected), args.batch_size):
            batch = selected[offset:offset+args.batch_size]
            audio, good = [], []
            for old in batch:
                path = Path(old['output'])
                if not path.is_absolute():
                    path = root / path
                record = dict(relative_path=old['relative_path'], audio_path=str(path),
                              original_status=old['status'], original_label=old['label'],
                              source_name=old['source_name'], single_instrument_verified='no')
                try:
                    wave, duration = load_audio(path)
                    record['duration_s'] = round(duration, 6)
                    audio.append(wave)
                    good.append(record)
                except (OSError, ValueError, sf.SoundFileError) as error:
                    record.update(error=str(error), comparison='error')
                    rows.append(record)
                    log.write(json.dumps(record, ensure_ascii=False)+'\n')
            if good:
                # The pinned Transformers 4.x extractor accepts raw_speech explicitly.
                features = processor.feature_extractor(audio, sampling_rate=48000, return_tensors='pt',
                                                       padding='repeatpad', truncation='rand_trunc').to(device)
                with torch.inference_mode():
                    embeddings = torch.nn.functional.normalize(model.get_audio_features(**features), dim=-1)
                    scores = (embeddings @ text_features.T).float().cpu().numpy()
                for record, score in zip(good, scores):
                    order = np.argsort(-score)
                    top = [{'label': labels[i], 'cosine': round(float(score[i]), 6)} for i in order[:5]]
                    record['top5'] = top
                    for rank in range(3):
                        record[f'top{rank+1}_label'] = top[rank]['label']
                        record[f'top{rank+1}_cosine'] = top[rank]['cosine']
                    record['top1_top2_margin'] = round(top[0]['cosine']-top[1]['cosine'], 6)
                    original = record['original_label']
                    record['original_rank'] = int(np.flatnonzero(order == labels.index(original))[0])+1 if original in labels else 0
                    record['original_cosine'] = round(float(score[labels.index(original)]), 6) if original in labels else ''
                    record['comparison'] = ('suggested_non_percussion_or_mixture' if top[0]['label'] in OTHER_SOUNDS else
                                            'suggested_label_for_unknown' if not original else
                                            'agrees_with_metadata' if top[0]['label'] == original else 'disagrees_with_metadata')
                    rows.append(record)
                    log.write(json.dumps(record, ensure_ascii=False)+'\n')
            log.flush()
            elapsed = time.monotonic()-started
            if offset == 0 or len(rows) % (args.batch_size * 10) == 0 or len(rows) == len(selected):
                print(f'{len(rows)}/{len(selected)} files | {elapsed:.1f}s | {len(rows)/max(elapsed,.01):.2f} files/s', flush=True)
    summary = summarize(rows, manifest, output, config)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('accepted_by_label','notes')}, ensure_ascii=False, indent=2))
    print(f'Report: {output / "REPORT.md"}')


if __name__ == '__main__':
    main()
