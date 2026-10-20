#!/usr/bin/env python3
"""Re-extract the existing A/B/C definitions on filtered_output, not the legacy inventory."""
from pathlib import Path
import json
import trich_xuat_dac_trung as feature
root = Path(__file__).resolve().parent.parent / 'filtered_output'
summary = json.loads((root / 'summary.json').read_text())
assert summary['total_audio_files'] == 655 and summary['classes'] == 13, 'Dataset version changed; review report before rebuilding.'
feature.HERE = root
feature.OUT = root / 'features'
if __name__ == '__main__':
    feature.main(dataset_root=root)
