import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

import percussion_filter as tool


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'input'
        self.source.mkdir()
        self.output = self.root / 'output'

    def tearDown(self):
        self.temp.cleanup()

    def audio(self, name, duration=.25, frequency=220, data=None, subtype='PCM_16'):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        t = np.arange(round(16000 * duration)) / 16000
        samples = .6 * np.sin(2 * np.pi * frequency * t) * np.exp(-t * 35) if data is None else data
        sf.write(path, samples, 16000, subtype=subtype)
        return path

    def run_filter(self, *extra):
        args = tool.parser().parse_args(['--input', str(self.source), '--output', str(self.output), *extra])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(tool.run(args), 0)
        with (self.output / 'manifest.csv').open(encoding='utf-8-sig') as f:
            return {r['relative_path']: r for r in csv.DictReader(f)}

    def test_short_valid_file_copied_unchanged(self):
        original = self.audio('snare001.wav', duration=.3)
        before = original.read_bytes()
        row = self.run_filter()['snare001.wav']
        self.assertEqual(row['status'], 'accepted')
        self.assertEqual(row['label'], 'snare')
        self.assertEqual(Path(row['output']).read_bytes(), before)
        self.assertEqual(original.read_bytes(), before)

    def test_silence_corruption_and_tiny_files_rejected(self):
        self.audio('kick_silent.wav', data=np.zeros(16000))
        self.audio('kick_tiny.wav', duration=.005)
        (self.source / 'snare_bad.wav').write_text('not audio')
        rows = self.run_filter()
        self.assertTrue(all(r['status'] == 'rejected' for r in rows.values()))
        self.assertIn('decode_error', rows['snare_bad.wav']['reasons'])
        self.assertFalse((self.output / 'accepted').exists())

    def test_freesound_numeric_id_metadata(self):
        self.audio('102780.wav')
        metadata = self.root / 'licenses.txt'
        metadata.write_text(json.dumps({'102780': {'name': 'acoustic_closed_hihat1.wav',
                                                  'username': 'snare_user', 'license': 'CC-BY'}}))
        row = self.run_filter('--metadata', str(metadata))['102780.wav']
        self.assertEqual(row['status'], 'accepted')
        self.assertEqual(row['label'], 'hi_hat')
        self.assertEqual(row['license'], 'CC-BY')

    def test_ambiguous_unknown_and_mixture_need_review(self):
        self.audio('kick_snare.wav', frequency=80)
        self.audio('123.wav', frequency=100)
        self.audio('kick_drumloop.wav', frequency=120)
        rows = self.run_filter()
        self.assertTrue(all(r['status'] == 'review' for r in rows.values()))
        self.assertIn('ambiguous_labels', rows['kick_snare.wav']['reasons'])
        self.assertEqual(rows['123.wav']['label'], '')
        self.assertIn('possible_drum_mixture', rows['kick_drumloop.wav']['reasons'])

    def test_exact_audio_duplicates_across_containers(self):
        a = self.audio('aaa_unknown.wav')
        data, sr = sf.read(a)
        sf.write(self.source / 'snare.flac', data, sr, subtype='PCM_16')
        rows = self.run_filter()
        self.assertEqual(rows['snare.flac']['status'], 'accepted')
        self.assertEqual(rows['aaa_unknown.wav']['status'], 'duplicate')
        self.assertEqual(rows['aaa_unknown.wav']['duplicate_of'], 'snare.flac')

    def test_conflicting_duplicate_labels_are_not_accepted(self):
        self.audio('kick.wav')
        self.audio('snare.wav')
        rows = self.run_filter()
        self.assertEqual(sorted(r['status'] for r in rows.values()), ['duplicate', 'review'])
        self.assertTrue(all('duplicate_label_conflict' in r['warnings'] for r in rows.values()))

    def test_stereo_opposite_phase_not_treated_as_silence(self):
        t = np.arange(8000) / 16000
        x = .5 * np.sin(2 * np.pi * 200 * t) * np.exp(-t * 25)
        self.audio('marimba.wav', data=np.column_stack([x, -x]))
        self.assertEqual(self.run_filter()['marimba.wav']['status'], 'accepted')

    def test_clipped_and_nonfinite_audio(self):
        self.audio('snare_clipped.wav', data=np.ones(16000))
        x = np.zeros(16000); x[100] = np.nan
        self.audio('kick_nan.wav', data=x, subtype='FLOAT')
        rows = self.run_filter()
        self.assertEqual(rows['snare_clipped.wav']['status'], 'review')
        self.assertIn('possible_clipping', rows['snare_clipped.wav']['warnings'])
        self.assertEqual(rows['kick_nan.wav']['status'], 'rejected')

    def test_overrides_and_exclusion(self):
        self.audio('123.wav', frequency=80)
        self.audio('456.wav', frequency=200)
        override = self.root / 'manual.csv'
        override.write_text('file,label\n123.wav,woodblock\n456.wav,exclude\n')
        rows = self.run_filter('--overrides', str(override))
        self.assertEqual(rows['123.wav']['label'], 'woodblock')
        self.assertEqual(rows['123.wav']['status'], 'accepted')
        self.assertEqual(rows['456.wav']['status'], 'rejected')

    def test_dry_run_and_existing_output_protection(self):
        self.audio('kick.wav')
        rows = self.run_filter('--dry-run')
        self.assertFalse(Path(rows['kick.wav']['output']).exists())
        self.assertTrue(json.loads((self.output / 'summary.json').read_text())['dry_run'])
        args = tool.parser().parse_args(['--input', str(self.source), '--output', str(self.output)])
        with self.assertRaisesRegex(ValueError, 'already exists'):
            tool.run(args)

    def test_same_name_in_different_folders_never_overwrites(self):
        self.audio('a/kick.wav', frequency=80)
        self.audio('b/kick.wav', frequency=100)
        rows = self.run_filter()
        destinations = {r['output'] for r in rows.values()}
        self.assertEqual(len(destinations), 2)
        self.assertTrue(all(Path(p).exists() for p in destinations))

    def test_word_boundaries_and_ignored_username(self):
        self.assertEqual(tool.guess_label(Path('tomato.wav'), {'username': 'snare'})[0], '')
        self.assertEqual(tool.guess_label(Path('Marimba.cord.ff.C2B2.aif'), {})[0], 'marimba')


if __name__ == '__main__':
    unittest.main()
