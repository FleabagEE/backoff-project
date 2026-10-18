"""Regression checks for physical-channel routing and recoverable data collection."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from collection import CollectionSession, atomic_npz, export_session
from stream_reader import StreamReaderPyAudio
from stream_analyzer import StreamAnalyzer
from device_check import RmsWindows, append_summary


class DiagnosticLevelTests(unittest.TestCase):
    def test_rms_windows_span_capture_block_boundaries(self):
        windows = RmsWindows(rate=1000, channels=2)
        samples = np.column_stack([np.zeros(100), np.r_[np.full(50, 0.1), np.full(50, 0.3)]])
        for part in (samples[:17], samples[17:81], samples[81:]):
            windows.append(part)
        values = np.asarray(windows.values)
        np.testing.assert_allclose(values[:, 1], [0.1, 0.3])
        self.assertAlmostEqual(float(np.median(values[:, 1])), 0.2)
        self.assertAlmostEqual(float(np.percentile(values[:, 1], 10)), 0.12)

    def test_measurement_discards_warmup_and_saves_complete_summary(self):
        import argparse
        import csv
        import device_check

        class FakeStream:
            samplerate = 48000
            def __init__(self, **kwargs):
                self.cursor = 0
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, size):
                index = np.arange(self.cursor, self.cursor + size)
                self.cursor += size
                right = np.where(index < 2400, 32767, np.where(index < 4800, 3276, 6553))
                return np.column_stack([np.full(size, 100), right]).astype(np.int16), False

        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'summary.csv'
            args = argparse.Namespace(device=15, channels=2, rate=48000, seconds=0.1,
                interval=0.05, label='synthetic', gain_note='test', warmup_seconds=0.05,
                csv=str(Path(root)/'intervals.csv'), summary_csv=str(path))
            with patch.object(device_check.sd, 'query_hostapis', return_value=[{'name': 'fake API'}]), \
                 patch.object(device_check.sd, 'query_devices', return_value={'name': 'fake', 'hostapi': 0, 'max_input_channels': 2}), \
                 patch.object(device_check.sd, 'InputStream', FakeStream), contextlib.redirect_stdout(io.StringIO()):
                device_check.run(args)
            with path.open(newline='', encoding='utf-8') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            right = rows[1]
            self.assertEqual(right['complete'], 'True')
            self.assertEqual(int(right['rms_window_count']), 2)
            self.assertAlmostEqual(float(right['captured_s']), 0.1)
            self.assertAlmostEqual(float(right['median_rms_fs']), (3276+6553)/2/32768)
            self.assertAlmostEqual(float(right['p10_rms_fs']), (0.9*3276+0.1*6553)/32768)
            self.assertAlmostEqual(float(right['max_peak_fs']), 6553/32768)
            self.assertEqual(float(right['clip_pct']), 0)

    def test_incompatible_summary_header_does_not_corrupt_existing_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'summary.csv'
            append_summary(path, [{'label': 'original', 'value': 1}])
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                append_summary(path, [{'different': 2}])
            self.assertEqual(path.read_bytes(), before)


class ChannelTests(unittest.TestCase):
    def make_pa(self):
        pa = MagicMock()
        pa.get_device_info_by_index.return_value = {
            'name': 'fake UM2', 'maxInputChannels': 2, 'defaultSampleRate': 48000}
        return pa

    def test_right_channel_reaches_original_fft_without_interleaving(self):
        pa = self.make_pa()
        with patch('stream_reader.pyaudio.PyAudio', return_value=pa), contextlib.redirect_stdout(io.StringIO()):
            ear = StreamAnalyzer(device=15, rate=48000, channels=2, input_channel=1,
                                 allow_fallback=False, n_frequency_bins=512, FFT_window_size_ms=50)
            reader = ear.stream_reader
            self.assertEqual(pa.open.call_args.kwargs['channels'], 2)
            self.assertEqual(pa.open.call_args.kwargs['frames_per_buffer'], 480)
            self.assertFalse(pa.open.call_args.kwargs['start'])
            # Deliberately different left/right signals prove routing, not just shape.
            right = (5000*np.sin(2*np.pi*1000*np.arange(2400)/48000)).astype(np.int16)
            for block in right.reshape(5, 480):
                stereo = np.column_stack([np.full(480, -20000, dtype=np.int16), block])
                reader.non_blocking_stream_read(stereo.tobytes(), 480, None, 0)
            np.testing.assert_array_equal(reader.data_buffer.get_most_recent(2400), right)
            frequencies, features, _, _ = ear.get_audio_features()
            self.assertEqual(len(features), 1200)
            self.assertEqual(ear.FFT_window_size, 2400)
            self.assertEqual(ear.rate, 48000)
            self.assertTrue(np.isfinite(features).all())
            self.assertGreater(np.max(features), 10000)
            self.assertEqual(ear.num_ffts, 1)
            ear.get_audio_features()
            self.assertEqual(ear.num_ffts, 1, 'Cached audio must not create another FFT update')
            self.assertEqual(reader.num_data_captures, 5)
            self.assertLess(ear.pcm_peak, 5100)
            self.assertGreater(ear.pcm_peak, 4900)
            self.assertAlmostEqual(ear.pcm_rms, np.sqrt(np.mean(right.astype(float)**2)))
            self.assertTrue(reader.test_device(15, 48000))
            self.assertEqual(pa.open.call_args.kwargs['channels'], 2)

    def test_fixed_profile_does_not_silently_fallback(self):
        import models
        with patch.object(models, 'StreamAnalyzer') as analyzer:
            models.get_ear(15)
            self.assertEqual(analyzer.call_args.kwargs['rate'], 48000)
            self.assertEqual(analyzer.call_args.kwargs['input_channel'], 1)
            self.assertFalse(analyzer.call_args.kwargs['allow_fallback'])


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.session = CollectionSession({'feature_count': 1200, 'sample_rate': 48000}, self.tmp.name)

    def save(self, name, value=1, **notes):
        return self.session.save_take(name, np.full((4, 1200), value),
                                      [0.03, 0.06, 0.09, 0.12], [0.01]*4, [0.2]*4,
                                      performer='A', variation='near, firm', duration_s=0.15, **notes)

    def test_export_is_recoverable_without_the_gui_or_pickle(self):
        self.save('knock', 2)
        self.save('rub', 3)
        path = export_session(self.session.path)
        with np.load(path, allow_pickle=False) as data:
            self.assertEqual(data['X'].shape, (8, 1200))
            self.assertEqual(data['X'].dtype, np.float32)
            self.assertEqual(len(set(data['take_ids'])), 2)
            self.assertEqual(data['elapsed_s'].shape, (8,))
            for features, label in zip(data['X'], data['y']):
                expected = {'knock': 2, 'rub': 3}[str(data['class_names'][label])]
                self.assertTrue(np.all(features == expected))
            self.assertEqual(json.loads(str(data['config_json']))['sample_rate'], 48000)

    def test_clear_preserves_original_but_omits_it_from_reexport(self):
        first = self.save('knock')
        self.save('rub')
        self.session.export()
        self.session.exclude_class('knock')
        self.assertFalse(first.exists())
        self.assertTrue(first.with_name(first.stem+'.excluded.npz').exists())
        self.assertFalse((self.session.path/'dataset.npz').exists())
        self.assertEqual(len(list(self.session.path.glob('dataset_before_clear_*.npz'))), 1)
        with np.load(self.session.export(), allow_pickle=False) as data:
            self.assertEqual(data['class_names'].tolist(), ['rub'])
            self.assertEqual(len(data['X']), 4)

    def test_invalid_take_is_archived_but_not_trained(self):
        self.save('neutral')
        excluded = self.save('knock', valid=False, reason='Audio stale')
        self.assertIn('.excluded.', excluded.name)
        with np.load(self.session.export(), allow_pickle=False) as data:
            self.assertEqual(len(data['X']), 4)
            self.assertEqual(data['class_names'].tolist(), ['neutral'])

    def test_holdout_split_survives_export_and_is_not_training_eligible(self):
        from collection import training_eligible
        self.save('knock', split='train')
        self.save('rub', split='holdout')
        with np.load(self.session.export(), allow_pickle=False) as data:
            self.assertEqual(int(np.sum(data['split'] == 'holdout')), 4)
            notes = json.loads(str(data['takes_json']))
            eligible = [n['class_name'] for n in notes if training_eligible(n)]
            self.assertEqual(eligible, ['knock'])
        self.assertIn('holdout', (self.session.path/'takes.csv').read_text(encoding='utf-8'))

    def test_failed_atomic_write_does_not_replace_saved_data(self):
        target = self.session.path / 'existing.npz'
        atomic_npz(target, X=np.array([1]))
        with patch('collection.os.replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                atomic_npz(target, X=np.array([2]))
        with np.load(target, allow_pickle=False) as data:
            np.testing.assert_array_equal(data['X'], [1])
        self.assertFalse(target.with_name(target.name+'.tmp').exists())

    def test_retry_after_log_failure_is_idempotent(self):
        with patch.object(self.session, 'write_log', side_effect=OSError('log error')):
            with self.assertRaises(OSError):
                self.save('knock', take_id='take_retry')
        self.save('knock', take_id='take_retry')
        self.assertEqual(len(self.session.take_paths()), 1)
        with np.load(self.session.export(), allow_pickle=False) as data:
            self.assertEqual(len(data['X']), 4)


if __name__ == '__main__':
    unittest.main()
