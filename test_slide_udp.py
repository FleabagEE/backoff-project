"""Live-label UDP forwarding to C's slide app. Synthetic predictions only; no audio."""
import json
from pathlib import Path
import queue
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import numpy as np

from models import EventDecisionConfig, EventDecoder
from slide_udp import LabelSender, parse_target
from visualizer import App

sys.path.insert(0, str(Path(__file__).resolve().parent / 'c_app'))
from gesture import ActionRule, SlideDeck    # noqa: E402  (C's app, stdlib only)
from udp_listener import UdpListener         # noqa: E402
from test_bakeoff_trial_gui import FakeWoodModel, frame   # noqa: E402  (B's event-mode fixtures)

MODEL_DIR = Path('a_models/wood_v3_20261019_135608_v1')
FPS = 21


def receive(sock, n, timeout=2.0):
    sock.settimeout(timeout)
    return [json.loads(sock.recvfrom(4096)[0]) for _ in range(n)]


class LabelSenderTests(unittest.TestCase):
    def setUp(self):
        self.rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx.bind(('127.0.0.1', 0))
        self.now = 0.0
        self.sender = LabelSender(self.rx.getsockname(), clock=lambda: 1234.5678,
                                  monotonic=lambda: self.now)

    def tearDown(self):
        self.sender.close()
        self.rx.close()

    def test_first_label_then_changes_only(self):
        stream = ['neutral', 'neutral', 'knock', 'knock', 'neutral', 'rub', 'knock', 'knock', 'neutral']
        sent = [label for label in stream if self.sender.update(label)]   # clock frozen: no heartbeats
        self.assertEqual(sent, ['neutral', 'knock', 'neutral', 'rub', 'knock', 'neutral'])
        got = receive(self.rx, len(sent))
        self.assertEqual([g['label'] for g in got], sent)
        self.assertEqual(got[0], {'label': 'neutral', 't': 1234.568})

    def test_heartbeat_repeats_current_label_while_frames_continue(self):
        sent = []
        for i in range(22):                                  # ~1 s of neutral frames
            self.now = i / FPS
            if self.sender.update('neutral'):
                sent.append(round(self.now, 3))
        self.assertEqual(len(sent), 8)                       # change + heartbeat every >= 0.1 s
        self.assertTrue(all(b - a >= 0.1 for a, b in zip(sent, sent[1:])))
        got = receive(self.rx, len(sent))
        self.assertNotIn('hb', got[0])
        self.assertTrue(all(g == {'label': 'neutral', 't': 1234.568, 'hb': True} for g in got[1:]))
        self.now = 5.0                                       # no update() calls -> nothing sent
        self.assertEqual(self.sender.heartbeats, 7)

    def test_change_is_sent_immediately_even_right_after_heartbeat(self):
        self.sender.update('neutral'); self.now = 0.1; self.sender.update('neutral')
        self.now = 0.101
        self.assertTrue(self.sender.update('knock'))

    def test_heartbeat_disabled(self):
        s = LabelSender(self.rx.getsockname(), monotonic=lambda: self.now, heartbeat_s=None)
        s.update('neutral'); self.now = 10.0
        self.assertFalse(s.update('neutral'))
        s.close()

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
    """Drive the real App.update() inference branch with fake fresh FFT frames.

    A fake clock advances 1/21 s per frame; it stamps both the sender's heartbeat
    timing and the "t" field, which the test then uses as arrival time for C's rule.
    """

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
        self.temp = tempfile.TemporaryDirectory()
        app.trial_log_root = Path(self.temp.name)
        app.build_ui()
        for name in ('neutral', 'knock', 'rub'):
            app.add_class(name)
        self.listener = UdpListener('127.0.0.1', 0).start()
        self.now = 0.0
        app.slide_sender = LabelSender(self.listener.address, clock=lambda: self.now,
                                       monotonic=lambda: self.now)
        self.app = app

    def tearDown(self):
        self.app.slide_sender.close()
        self.listener.close()
        dpg.destroy_context()
        self.temp.cleanup()

    def frames(self, n, amps=None, kinds=None):
        """Run update() n (or len(kinds)) times, each with one fresh FFT frame; return
        Prediction texts. kinds: B's Q/N/K/R frame string for event mode. The event
        decoder reads time.monotonic() itself, so the fake clock is patched in."""
        amps = np.zeros(1200, dtype=np.float32) if amps is None else amps
        freqs = np.arange(1, 1201, dtype=float) * 20
        per_frame = [frame(k) for k in kinds] if kinds is not None else None
        n = len(per_frame) if per_frame is not None else n
        calls = iter(range(n))

        def features(ear):
            ear.num_ffts += 1
            return freqs, per_frame[next(calls)] if per_frame is not None else amps
        shown = []
        with patch('visualizer.get_audio_features', side_effect=features), \
                patch('visualizer.time.monotonic', lambda: self.now):
            for _ in range(n):
                self.app.update()
                shown.append(dpg.get_value('prediction').removeprefix('Prediction: '))
                self.now = round(self.now + 1 / FPS, 6)
        return shown

    def drain(self):
        out = []
        while True:
            try:
                out.append(self.listener.out.get(timeout=0.3))
            except queue.Empty:
                return out

    def start_infer(self, predictor, classes=('neutral', 'knock', 'rub')):
        self.app.wood_predictor = predictor
        self.app.model = getattr(predictor, 'model', object())
        self.app.infer_classes = list(classes)
        dpg.set_value('mode', 'Infer'); self.app.mode_callback(None, 'Infer')

    def test_simulated_predictions_reach_slides(self):
        # PER-WINDOW mode (--decision window, or a model loaded via Load Model): the GUI
        # publishes every window's label. Not the live default any more; kept to show
        # why that mode must not drive the slides.
        seq = ([0] * 20 + [1] * 2 + [0] * 25        # knock            -> change msg: knock
               + [2] * 15 + [0] * 25                # scratch          -> change msg: rub
               + [1] * 1 + [2] * 3 + [0] * 25       # knock->rub, no neutral between: two changes
               + [2] * 2 + [0] * 8 + [2] * 3        # rub, 0.38 s neutral, rub: two rub changes
               + [0] * 20)
        it = iter(seq)
        self.start_infer(SimpleNamespace(predict_windows=lambda X: np.array([next(it)] * len(X))))
        shown = self.frames(len(seq))

        names = ['neutral', 'knock', 'rub']
        self.assertEqual(shown, [names[i] for i in seq])           # GUI Prediction stream
        items = self.drain()
        msgs = [m[1] for m in items]
        # Every change point of the GUI stream is sent, in order, at its frame time.
        changes = [(round(i / FPS, 3), shown[i]) for i in range(len(shown))
                   if i == 0 or shown[i] != shown[i - 1]]
        sent_changes = [(m.t, m.label) for m in msgs if not m.hb]
        self.assertEqual(sent_changes, changes)
        # Heartbeats only repeat the current GUI label; never a label the GUI did not show.
        for m in msgs:
            self.assertEqual(shown[round(m.t * FPS)], m.label)
        self.assertGreater(len(msgs), len(changes))                 # heartbeats present

        # C's rule executes EVERY non-heartbeat knock/rub message once and never turns
        # on a heartbeat. With per-window labels that means one page per label change:
        # knock->rub without neutral turns forward then back, and the split rub (rub,
        # short neutral, rub) turns back twice. The event decoder (default) is what
        # prevents this; per-window mode must not drive the slides.
        rule, deck, turns = ActionRule(), SlideDeck(10), []
        deck.index = 5
        for m in msgs:
            d = rule.feed(m.label, heartbeat=m.hb)
            if d.action:
                deck.apply(d.action); turns.append(d.action)
        self.assertEqual(turns, ['next', 'prev', 'next', 'prev', 'prev', 'prev'])
        self.assertEqual(rule.heartbeats, sum(m.hb for m in msgs))
        self.assertEqual(rule.actions, 6)
        self.assertEqual(deck.index, 3)

    def start_event_mode(self):
        """B's live path: --trained-model with the default --decision event."""
        self.start_infer(SimpleNamespace(model=FakeWoodModel()))
        self.app.event_decoder = EventDecoder(EventDecisionConfig(trigger_energy=1.0, vote_energy=1.0),
                                              self.app.infer_classes)

    def received(self):
        """(Message list, raw datagram list) in arrival order."""
        items = self.drain()
        return [m[1] for m in items], [m[2] for m in items]

    def test_event_mode_sends_one_action_message_per_decided_event(self):
        """B's EventDecoder -> publish_label -> LabelSender -> UDP -> C's listener -> ActionRule.

        Two separate knocks, a scratch, then knock followed by a scratch with the
        shortest quiet gap that lets the decoder close the knock. C must turn
        next, next, prev, next, prev; heartbeats and neutral must turn nothing."""
        self.start_event_mode()
        dpg.set_value('bakeoff_trial_type', 'knock_pos')
        self.app.space_shortcut(); self.app.release_space_key()     # SPACE: trial start
        self.assertTrue(self.app.trial.active)
        kinds = ('Q' * 10 + 'KKKK' + 'Q' * 25            # knock #1
                 + 'KKKK' + 'Q' * 25                     # knock #2, independent event
                 + 'R' * 22 + 'Q' * 25                   # scratch (~1 s): decided at max_s
                 + 'KKKK' + 'Q' * 12 + 'R' * 22 + 'Q' * 25)  # knock then scratch, short gap
        shown = self.frames(0, kinds=kinds)
        self.app.space_shortcut(); self.app.release_space_key()     # SPACE: trial stop
        self.assertFalse(self.app.trial.active)

        msgs, raws = self.received()
        actions = [m.label for m in msgs if not m.hb]
        # The wire carries exactly one non-heartbeat knock/rub message per decided
        # event, always separated by a neutral change (the 0.25 s hold ends).
        self.assertEqual(actions, ['neutral', 'knock', 'neutral', 'knock', 'neutral', 'rub',
                                   'neutral', 'knock', 'neutral', 'rub', 'neutral'])
        self.assertTrue(any(m.hb and m.label == 'knock' for m in msgs))   # held label heartbeats
        self.assertTrue(any(m.hb and m.label == 'neutral' for m in msgs))
        for m in msgs:                                   # every datagram repeats a shown label
            self.assertEqual(shown[round(m.t * FPS)], m.label)
        # Actual protocol: only label, t and (on heartbeats) hb. No event id, type or session.
        for raw in raws:
            self.assertLessEqual(set(json.loads(raw)), {'label', 't', 'hb'}, raw)

        rule, deck, turns = ActionRule(), SlideDeck(10), []
        deck.index = 4
        for m in msgs:
            d = rule.feed(m.label, heartbeat=m.hb)
            if d.action:
                deck.apply(d.action); turns.append(d.action)
        self.assertEqual(turns, ['next', 'next', 'prev', 'next', 'prev'])
        self.assertEqual(deck.index, 5)
        self.assertEqual(rule.actions, 5)
        self.assertEqual(rule.heartbeats, sum(m.hb for m in msgs))
        # GUI display, UDP and the SPACE trial SET come from the same publish_label call.
        trial = self.app.trial.history[-1]
        self.assertEqual(trial['label_set'], sorted({m.label for m in msgs}))
        self.assertEqual(trial['labels'], shown)
        self.assertEqual(trial['label_set'], ['knock', 'neutral', 'rub'])

    def test_event_mode_scratch_onset_knock_never_reaches_slides(self):
        """A's live scratch #1 (K x5 -> R x20 -> K): per-window output turned a page
        forward; the event decoder sends only one rub, so C goes back one page."""
        self.start_event_mode()
        self.frames(0, kinds='Q' * 10 + 'K' * 5 + 'R' * 20 + 'K' + 'Q' * 30)
        msgs, _ = self.received()
        self.assertEqual([m.label for m in msgs if not m.hb], ['neutral', 'rub', 'neutral'])
        rule, deck = ActionRule(), SlideDeck(3)
        deck.index = 1
        for m in msgs:
            d = rule.feed(m.label, heartbeat=m.hb)
            if d.action:
                deck.apply(d.action)
        self.assertEqual((deck.index, rule.actions), (0, 1))

    def test_event_mode_quiet_and_noise_turn_nothing(self):
        self.start_event_mode()
        self.frames(0, kinds='Q' * 20 + 'N' + 'Q' * 10 + 'NNK' + 'Q' * 30)   # neutral majority
        msgs, _ = self.received()
        self.assertEqual([m.label for m in msgs if not m.hb], ['neutral'])
        self.assertGreater(len(msgs), 1)                                   # heartbeats only
        rule = ActionRule()
        self.assertEqual([rule.feed(m.label, heartbeat=m.hb).action for m in msgs],
                         [None] * len(msgs))

    def test_reentering_infer_resends_current_label(self):
        self.app.slide_sender.heartbeat_s = None                     # isolate reset behaviour
        self.start_infer(SimpleNamespace(predict_windows=lambda X: np.zeros(len(X), int)))
        self.frames(5)
        dpg.set_value('mode', 'Train'); self.app.mode_callback(None, 'Train')
        self.frames(3)                                               # Train: nothing sent
        dpg.set_value('mode', 'Infer'); self.app.mode_callback(None, 'Infer')
        self.frames(3)
        self.assertEqual([m[1].label for m in self.drain()], ['neutral', 'neutral'])

    def test_train_mode_sends_no_heartbeats(self):
        self.start_infer(SimpleNamespace(predict_windows=lambda X: np.zeros(len(X), int)))
        self.frames(3)
        dpg.set_value('mode', 'Train'); self.app.mode_callback(None, 'Train')
        before = len(self.drain())
        self.frames(40)                                              # ~2 s, no inference
        self.assertEqual(len(self.drain()), 0)
        self.assertGreater(before, 0)

    @unittest.skipUnless((MODEL_DIR / 'model.joblib').exists(), 'wood v3 model not present')
    def test_real_wood_v3_pair_quiet_frames_send_neutral(self):
        from wood_v3_model import WoodV3Model
        p = WoodV3Model(MODEL_DIR / 'model.joblib', MODEL_DIR / 'decision_params.json')
        self.start_infer(p, p.params['class_names'])
        self.assertEqual(set(self.frames(5)), {'neutral'})          # below the band gate
        self.assertEqual({m[1].label for m in self.drain()}, {'neutral'})


if __name__ == '__main__':
    unittest.main()
