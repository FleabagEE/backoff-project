"""Live-label UDP forwarding to C's slide app. Synthetic predictions only; no audio."""
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import numpy as np

from slide_udp import LabelSender, parse_target
from visualizer import App

sys.path.insert(0, str(Path(__file__).resolve().parent / 'c_app'))
from gesture import GestureGate, SlideDeck   # noqa: E402  (C's app, stdlib only)
from udp_listener import UdpListener         # noqa: E402

MODEL_DIR = Path('a_models/wood_v3_20261019_135608_v1')


def receive(sock, n, timeout=2.0):
    sock.settimeout(timeout)
    return [json.loads(sock.recvfrom(4096)[0]) for _ in range(n)]


class LabelSenderTests(unittest.TestCase):
    def setUp(self):
        self.rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx.bind(('127.0.0.1', 0))
        self.sender = LabelSender(self.rx.getsockname(), clock=lambda: 1234.5678)

    def tearDown(self):
        self.sender.close()
        self.rx.close()

    def test_first_label_then_changes_only(self):
        stream = ['neutral', 'neutral', 'knock', 'knock', 'neutral', 'rub', 'knock', 'knock', 'neutral']
        sent = [label for label in stream if self.sender.update(label)]
        self.assertEqual(sent, ['neutral', 'knock', 'neutral', 'rub', 'knock', 'neutral'])
        got = receive(self.rx, len(sent))
        self.assertEqual([g['label'] for g in got], sent)
        self.assertEqual(got[0], {'label': 'neutral', 't': 1234.568})

    def test_reset_resends_and_invalid_ignored(self):
        self.assertTrue(self.sender.update('neutral'))
        self.assertFalse(self.sender.update('neutral'))
        self.sender.reset()
        self.assertTrue(self.sender.update('neutral'))
        self.assertFalse(self.sender.update('tap'))
        self.assertFalse(self.sender.update(None))
        self.assertEqual(self.sender.sent, 2)

    def test_no_receiver_and_off(self):
        closed = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        closed.bind(('127.0.0.1', 0)); addr = closed.getsockname(); closed.close()
        s = LabelSender(addr)
        for label in ('neutral', 'knock', 'neutral') * 3:
            s.update(label)                    # must never raise
        s.close()
        off = LabelSender(parse_target('off'))
        self.assertFalse(off.update('knock'))

    def test_parse_target(self):
        self.assertEqual(parse_target('127.0.0.1:5005'), ('127.0.0.1', 5005))
        self.assertIsNone(parse_target('off'))
        for bad in ('5005', 'localhost:', ':5005', 'host:0', 'host:abc', 'host:70000'):
            with self.assertRaises(ValueError):
                parse_target(bad)


class GuiToSlideChainTests(unittest.TestCase):
    """Drive the real App.update() inference branch with fake fresh FFT frames."""

    def setUp(self):
        dpg.create_context()
        app = App.__new__(App)
        app.fast_takes = False; app.event_rhythm = False; app.record_key_held = False
        app.devices = {}; app.selected_device = None; app.session_type = 'final'
        app.scratch_surface = 'wood'; app.collected_data = {}; app.pending_take = None
        app.pending_holdout = None; app.is_recording = False; app.record_val = None
        app.unsaved = False; app.fault = None; app.plot_max = 1000.0; app.last_fft_time = None
        app.take_counts = {s: dict(knock=0, rub=0, neutral=0) for s in ('train', 'holdout')}
        app.trial_counts = {}
        app.ear = SimpleNamespace(num_ffts=10, pcm_rms=0, pcm_peak=0, stream_reader=SimpleNamespace(
            last_error=None, status_count=0, stream=SimpleNamespace(is_active=lambda: True)))
        app.healthy = lambda: True
        app.build_ui()
        for name in ('neutral', 'knock', 'rub'):
            app.add_class(name)
        self.listener = UdpListener('127.0.0.1', 0).start()
        app.slide_sender = LabelSender(self.listener.address)
        self.app = app

    def tearDown(self):
        self.app.slide_sender.close()
        self.listener.close()
        dpg.destroy_context()

    def frames(self, n, amps=None):
        """Run update() n times, each with one fresh FFT frame; return Prediction texts."""
        amps = np.zeros(1200, dtype=np.float32) if amps is None else amps
        freqs = np.arange(1, 1201, dtype=float) * 20

        def features(ear):
            ear.num_ffts += 1
            return freqs, amps
        shown = []
        with patch('visualizer.get_audio_features', side_effect=features):
            for _ in range(n):
                self.app.update()
                shown.append(dpg.get_value('prediction').removeprefix('Prediction: '))
        return shown

    def drain(self, expected):
        out = [self.listener.out.get(timeout=2) for _ in range(expected)]
        self.assertTrue(self.listener.out.empty() or self.listener.out.qsize() == 0)
        return out

    def test_simulated_predictions_reach_slides_once_per_action(self):
        # Simulated per-window final labels (21 frames/s style), as the GUI would show them.
        seq = ([0] * 10 + [1] * 2 + [0] * 25        # knock            -> next
               + [2] * 15 + [0] * 25                # scratch          -> previous
               + [1] * 1 + [2] * 3 + [0] * 25       # knock->rub, no neutral between -> next only
               + [1] * 1 + [0] * 2 + [1] * 1        # second knock 3 frames (~0.14 s) later
               + [0] * 20)                          #   -> one next, the second is cooled down
        it = iter(seq)
        self.app.wood_predictor = SimpleNamespace(
            predict_windows=lambda X: np.array([next(it)] * len(X)))
        self.app.model = object(); self.app.infer_classes = ['neutral', 'knock', 'rub']
        dpg.set_value('mode', 'Infer'); self.app.mode_callback(None, 'Infer')
        shown = self.frames(len(seq))

        names = ['neutral', 'knock', 'rub']
        self.assertEqual(shown, [names[i] for i in seq])           # GUI Prediction stream
        change_at = [i for i in range(len(shown)) if i == 0 or shown[i] != shown[i - 1]]
        items = self.drain(len(change_at))
        self.assertEqual([m[1].label for m in items], [shown[i] for i in change_at])  # same stream
        self.assertTrue(all(isinstance(m[1].t, float) for m in items))

        # Feed C's gate with the frame time of each change (21 frames/s), since the
        # test produces all frames faster than real time.
        gate, deck, turns, reasons = GestureGate(0.8), SlideDeck(5), [], []
        for i, (kind, msg, raw, _) in zip(change_at, items):
            d = gate.feed(msg.label, i / 21)
            reasons.append(d.reason)
            if d.action:
                deck.apply(d.action); turns.append(d.action)
        self.assertEqual(turns, ['next', 'prev', 'next', 'next'])
        self.assertEqual(deck.index, 2)
        self.assertIn('rub: waiting for neutral', reasons)
        self.assertIn('knock: suppressed by cooldown', reasons)

    def test_reentering_infer_resends_current_label(self):
        self.app.wood_predictor = SimpleNamespace(predict_windows=lambda X: np.zeros(len(X), int))
        self.app.model = object(); self.app.infer_classes = ['neutral', 'knock', 'rub']
        dpg.set_value('mode', 'Infer'); self.app.mode_callback(None, 'Infer')
        self.frames(5)
        dpg.set_value('mode', 'Train'); self.app.mode_callback(None, 'Train')
        self.frames(3)                                               # Train: nothing sent
        dpg.set_value('mode', 'Infer'); self.app.mode_callback(None, 'Infer')
        self.frames(3)
        self.assertEqual([m[1].label for m in self.drain(2)], ['neutral', 'neutral'])

    @unittest.skipUnless((MODEL_DIR / 'model.joblib').exists(), 'wood v3 model not present')
    def test_real_wood_v3_pair_quiet_frames_send_neutral(self):
        from wood_v3_model import WoodV3Model
        p = WoodV3Model(MODEL_DIR / 'model.joblib', MODEL_DIR / 'decision_params.json')
        self.app.wood_predictor = p; self.app.model = p.model
        self.app.infer_classes = p.params['class_names']
        dpg.set_value('mode', 'Infer'); self.app.mode_callback(None, 'Infer')
        self.assertEqual(set(self.frames(5)), {'neutral'})          # below the band gate
        self.assertEqual([m[1].label for m in self.drain(1)], ['neutral'])


if __name__ == '__main__':
    unittest.main()
