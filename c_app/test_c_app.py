"""python -m unittest discover -s c_app -v   (standard library only)"""
import json
import queue
import socket
import time
import unittest

from gesture import NEXT, PREV, GestureGate, SlideDeck
from protocol import Message, parse_message
from udp_listener import PortInUseError, UdpListener


class ParseTests(unittest.TestCase):
    def test_plain_text(self):
        for raw in (b'knock', b'rub', b'neutral', b' Knock\r\n', 'RUB'):
            self.assertIsNotNone(parse_message(raw), raw)
        self.assertEqual(parse_message(b'knock'), Message('knock'))

    def test_json_string(self):
        self.assertEqual(parse_message(b'"rub"'), Message('rub'))
        self.assertEqual(parse_message(json.dumps('neutral').encode()), Message('neutral'))

    def test_json_object(self):
        self.assertEqual(parse_message(b'{"label":"knock","t":123.4}'), Message('knock', 123.4))
        self.assertEqual(parse_message(b'{"label":"rub"}'), Message('rub'))
        self.assertEqual(parse_message(b'{"label":"rub","t":"x"}'), Message('rub'))
        self.assertEqual(parse_message(b'{"label":"rub","t":true}'), Message('rub'))

    def test_invalid_never_raises(self):
        for raw in (b'', b'   ', b'tap', b'scratch', b'"tap"', b'{"label":"jump"}', b'{}',
                    b'{"t":1}', b'{"label":1}', b'[1,2]', b'123', b'null', b'\xff\xfe',
                    b'{"label": "knock"', b'[' * 5000, b'k' * 5000, None, 42):
            self.assertIsNone(parse_message(raw), raw if raw is None else repr(raw)[:30])


def run(gate, labels, start=100.0, dt=1 / 21):
    """Feed a frame stream; return list of (time, action) for triggers."""
    out = []
    for i, label in enumerate(labels):
        t = start + i * dt
        d = gate.feed(label, t)
        if d.action:
            out.append((round(t - start, 3), d.action))
    return out


def neutral(gate, t0, t1, step=0.1):
    """Neutral change at t0 plus heartbeats every `step` up to t1 (like slide_udp)."""
    d, t = None, t0
    while t <= t1 + 1e-9:
        d = gate.feed('neutral', round(t, 6))
        t += step
    return d


def armed_gate(**kw):
    g = GestureGate(**kw)
    neutral(g, -3.0, -1.0)
    assert g.armed
    return g


class GateTests(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(armed_gate().feed('knock', 0).action, NEXT)
        self.assertEqual(armed_gate().feed('rub', 0).action, PREV)
        self.assertIsNone(armed_gate().feed('neutral', 0).action)

    def test_starts_disarmed(self):
        g = GestureGate()
        self.assertFalse(g.armed)
        self.assertIsNone(g.feed('knock', 0).action)

    def test_regression_single_neutral_message_does_not_rearm(self):
        # Reported bug: rub@0.1, neutral@0.5, rub@1.0 turned two pages (change-only sender).
        g = armed_gate()
        self.assertEqual(g.feed('rub', 0.1).action, PREV)
        g.feed('neutral', 0.5)
        d = g.feed('rub', 1.0)
        self.assertIsNone(d.action)
        self.assertIn('waiting for confirmed neutral', d.reason)

    def test_short_neutral_with_heartbeats_does_not_rearm(self):
        g = armed_gate()
        g.feed('rub', 0.1)
        neutral(g, 0.5, 0.9)                         # 0.4 s of evidence < 0.6 s hold
        self.assertIsNone(g.feed('rub', 1.0).action)

    def test_silence_is_not_neutral(self):
        g = armed_gate()
        g.feed('knock', 0.0)
        g.feed('neutral', 0.2)
        g.feed('neutral', 1.5)                       # 1.3 s gap > max_gap: chain restarts
        self.assertFalse(g.armed)
        self.assertIsNone(g.feed('knock', 1.6).action)
        g = armed_gate()
        g.feed('knock', 0.0)
        g.feed('neutral', 0.2)                       # then nothing at all
        self.assertIsNone(g.feed('knock', 5.0).action)

    def test_broken_chain_restarts(self):
        g = armed_gate()
        g.feed('rub', 0.0)
        neutral(g, 0.1, 0.5)
        neutral(g, 1.0, 1.4)                         # 0.5 s gap broke the chain at 1.0
        self.assertFalse(g.armed)
        self.assertIsNone(g.feed('rub', 1.5).action)
        neutral(g, 1.6, 2.3)
        self.assertTrue(g.armed)
        self.assertEqual(g.feed('rub', 2.4).action, PREV)

    def test_confirmed_neutral_rearms(self):
        g = armed_gate()
        self.assertEqual(g.feed('rub', 0.1).action, PREV)
        d = neutral(g, 0.5, 1.1)                     # 0.6 s of continuous evidence
        self.assertTrue(g.armed)
        self.assertIn('re-armed', d.reason)
        self.assertEqual(g.feed('rub', 1.2).action, PREV)

    def test_neutral_hold_configurable(self):
        g = armed_gate(neutral_hold_s=0)              # first neutral message re-arms
        g.feed('knock', 0.0); g.feed('neutral', 0.9)
        self.assertEqual(g.feed('knock', 1.0).action, NEXT)
        g = armed_gate(neutral_hold_s=1.5)
        g.feed('knock', 0.0); neutral(g, 0.1, 1.2)
        self.assertFalse(g.armed)
        with self.assertRaises(ValueError):
            GestureGate(neutral_hold_s=-1)
        with self.assertRaises(ValueError):
            GestureGate(max_gap_s=0)

    def test_repeated_label_turns_once(self):
        actions = run(GestureGate(), ['neutral'] * 21 + ['knock'] * 63 + ['neutral'] * 5)
        self.assertEqual([a for _, a in actions], [NEXT])

    def test_needs_neutral_between_actions(self):
        g = armed_gate(cooldown_s=0)
        self.assertEqual(g.feed('knock', 0).action, NEXT)
        self.assertIsNone(g.feed('rub', 0.1).action)      # no neutral since the knock
        self.assertIsNone(g.feed('knock', 0.2).action)
        neutral(g, 0.3, 1.0)
        self.assertEqual(g.feed('rub', 1.1).action, PREV)

    def test_cooldown(self):
        g = armed_gate(cooldown_s=0.8, neutral_hold_s=0.3)
        self.assertEqual(g.feed('knock', 0.0).action, NEXT)
        neutral(g, 0.1, 0.4)
        d = g.feed('knock', 0.5)
        self.assertIsNone(d.action)
        self.assertIn('cooldown', d.reason)
        # The suppressed knock also disarmed: still held after cooldown -> nothing.
        self.assertIsNone(g.feed('knock', 1.5).action)
        neutral(g, 1.6, 2.0)
        self.assertEqual(g.feed('knock', 2.1).action, NEXT)

    def test_cooldown_boundary_and_config(self):
        g = armed_gate(cooldown_s=0.8, neutral_hold_s=0.3)
        g.feed('knock', 0.0); neutral(g, 0.1, 0.7)
        self.assertEqual(g.feed('rub', 0.8).action, PREV)
        g = armed_gate(cooldown_s=2.0)
        g.feed('knock', 0.0); neutral(g, 0.1, 1.4)
        self.assertIsNone(g.feed('rub', 1.5).action)
        with self.assertRaises(ValueError):
            GestureGate(cooldown_s=-1)

    def test_mock_sequence(self):
        f = lambda label, s: [label] * round(s * 21)
        stream = (f('neutral', 1) + f('knock', .3) + f('neutral', 1) + f('knock', .3)
                  + f('neutral', 1) + f('rub', 1) + f('neutral', 1))
        self.assertEqual([a for _, a in run(GestureGate(), stream)], [NEXT, NEXT, PREV])


class DeckTests(unittest.TestCase):
    def test_bounds(self):
        d = SlideDeck(3)
        self.assertFalse(d.apply(PREV)); self.assertEqual(d.index, 0)
        self.assertTrue(d.apply(NEXT)); self.assertTrue(d.apply(NEXT))
        self.assertFalse(d.apply(NEXT)); self.assertEqual(d.index, 2)
        self.assertTrue(d.apply(PREV)); self.assertEqual(d.index, 1)
        self.assertFalse(d.apply(None))

    def test_single_slide(self):
        d = SlideDeck(1)
        self.assertFalse(d.apply(NEXT)); self.assertFalse(d.apply(PREV))
        with self.assertRaises(ValueError):
            SlideDeck(0)


class ListenerTests(unittest.TestCase):
    def test_receives_and_reports_invalid(self):
        listener = UdpListener('127.0.0.1', 0).start()
        try:
            tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for payload in (b'knock', b'garbage', b'{"label":"rub","t":1.5}', b'"neutral"'):
                tx.sendto(payload, listener.address)
            tx.close()
            got = [listener.out.get(timeout=2) for _ in range(4)]
        finally:
            listener.close()
        self.assertEqual([g[0] for g in got], ['msg', 'invalid', 'msg', 'msg'])
        self.assertEqual(got[0][1], Message('knock'))
        self.assertEqual(got[2][1], Message('rub', 1.5))

    def test_port_in_use(self):
        first = UdpListener('127.0.0.1', 0)
        try:
            with self.assertRaises(PortInUseError) as ctx:
                UdpListener('127.0.0.1', first.address[1])
            self.assertIn('--port', str(ctx.exception))
        finally:
            first.close()


class SlideFolderTests(unittest.TestCase):
    def test_folder_and_fallback(self):
        import tempfile
        from pathlib import Path
        from slide_demo import load_slides
        with tempfile.TemporaryDirectory() as d:
            slides, _ = load_slides(d)                       # empty -> built-in 3 pages
            self.assertEqual(len(slides), 3)
            for name in ('10.png', '02.JPG', '01.jpeg', 'notes.txt'):
                (Path(d) / name).write_bytes(b'x')
            slides, _ = load_slides(d)
            self.assertEqual([s['path'].name for s in slides], ['01.jpeg', '02.JPG', '10.png'])

    def test_natural_sort(self):
        import tempfile
        from pathlib import Path
        from slide_demo import load_slides
        names = ['Slide10.png', '10.png', 'Slide2.png', '2.png', 'slide1.png', '1.png', 'Slide11.png']
        with tempfile.TemporaryDirectory() as d:
            for name in names:
                (Path(d) / name).write_bytes(b'x')
            got = [s['path'].name for s in load_slides(d)[0]]
        self.assertEqual(got, ['1.png', '2.png', '10.png', 'slide1.png', 'Slide2.png',
                               'Slide10.png', 'Slide11.png'])
        slides, warning = load_slides('definitely/not/here')
        self.assertEqual(len(slides), 3)
        self.assertIn('not found', warning)


class AppTests(unittest.TestCase):
    """Drives the real Tk window without sockets; skipped if no display."""

    def test_handle_messages(self):
        try:
            import tkinter as tk
            root = tk.Tk()
        except Exception as exc:  # no display / Tk
            self.skipTest(f'Tk unavailable: {exc}')
        root.withdraw()
        from slide_demo import BUILTIN_SLIDES, SlideApp

        class FakeListener:
            out = queue.Queue()
            address = ('127.0.0.1', 5005)
            def close(self): pass

        app = SlideApp(root, [dict(s) for s in BUILTIN_SLIDES], FakeListener(), None,
                       GestureGate(0.8))
        t0 = time.monotonic()

        def send(raw, dt):
            msg = parse_message(raw)
            app.handle(('invalid', raw, t0 + dt) if msg is None else ('msg', msg, raw, t0 + dt))

        def neutral_for(start, stop):
            dt = start
            while dt <= stop + 1e-9:
                send(b'{"label":"neutral","t":1,"hb":true}', dt); dt += 0.1

        try:
            neutral_for(0.0, 0.7)
            send(b'\xff', 0.75)
            send(b'knock', 0.8)                             # NEXT -> page 2
            self.assertIn('KNOCK', app.recognized_var.get())
            self.assertIn('NEXT', app.slide_var.get())
            neutral_for(1.2, 1.5)                           # too short to re-arm
            send(b'rub', 1.6)                               # recognized, NOT executed
            self.assertIn('RUB', app.recognized_var.get())
            self.assertIn('not turned (waiting for confirmed neutral)', app.slide_var.get())
            self.assertEqual(app.deck.index, 1)
            send(b'rub', 1.7)                               # repeat: display unchanged
            neutral_for(1.8, 2.5)
            send(b'{"label":"rub","t":2.0}', 2.6)           # PREVIOUS -> page 1
            self.assertIn('PREVIOUS', app.slide_var.get())
            app.update_status()
            self.assertIn('last valid message:', app.current_var.get())
            self.assertIn('rub', app.current_var.get())
            root.update()
            self.assertEqual(app.deck.index, 0)
            self.assertEqual(app.counts['turns'], 2)
            self.assertEqual(app.counts['invalid'], 1)
        finally:
            app.close()


if __name__ == '__main__':
    unittest.main()
