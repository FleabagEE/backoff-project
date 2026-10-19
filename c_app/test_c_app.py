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


class GateTests(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(GestureGate().feed('knock', 0).action, NEXT)
        self.assertEqual(GestureGate().feed('rub', 0).action, PREV)
        self.assertIsNone(GestureGate().feed('neutral', 0).action)

    def test_repeated_label_turns_once(self):
        actions = run(GestureGate(), ['neutral'] * 10 + ['knock'] * 63 + ['neutral'] * 5)
        self.assertEqual([a for _, a in actions], [NEXT])

    def test_needs_neutral_between_actions(self):
        g = GestureGate(cooldown_s=0)
        self.assertEqual(g.feed('knock', 0).action, NEXT)
        self.assertIsNone(g.feed('rub', 5).action)        # no neutral since the knock
        self.assertIsNone(g.feed('knock', 10).action)
        g.feed('neutral', 11)
        self.assertEqual(g.feed('rub', 12).action, PREV)

    def test_cooldown(self):
        g = GestureGate(cooldown_s=0.8)
        self.assertEqual(g.feed('knock', 0.0).action, NEXT)
        g.feed('neutral', 0.1)
        d = g.feed('knock', 0.5)
        self.assertIsNone(d.action)
        self.assertIn('cooldown', d.reason)
        # The suppressed knock also disarmed: still held after cooldown -> nothing.
        self.assertIsNone(g.feed('knock', 1.5).action)
        g.feed('neutral', 1.6)
        self.assertEqual(g.feed('knock', 1.7).action, NEXT)

    def test_cooldown_boundary_and_config(self):
        g = GestureGate(cooldown_s=0.8)
        g.feed('knock', 0.0); g.feed('neutral', 0.1)
        self.assertEqual(g.feed('rub', 0.8).action, PREV)
        g = GestureGate(cooldown_s=2.0)
        g.feed('knock', 0.0); g.feed('neutral', 0.1)
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
        try:
            t = time.monotonic()
            for i, raw in enumerate([b'neutral', b'\xff', b'knock', b'knock', b'neutral',
                                     b'rub', b'neutral']):
                msg = parse_message(raw)
                item = ('invalid', raw, t) if msg is None else ('msg', msg, raw, t + i)
                app.handle(item)
            root.update()
            self.assertEqual(app.deck.index, 0)       # next, then previous
            self.assertEqual(app.counts, dict(received=6, invalid=1, turns=2))
        finally:
            app.close()


if __name__ == '__main__':
    unittest.main()
