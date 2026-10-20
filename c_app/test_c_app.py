"""python -m unittest discover -s c_app -v   (standard library only)"""
import json
import queue
import socket
import time
import unittest

from gesture import NEXT, PREV, ActionRule, SlideDeck
from protocol import Message, parse_message
from udp_listener import PortInUseError, UdpListener


class ParseTests(unittest.TestCase):
    def test_plain_text(self):
        for raw in (b'knock', b'rub', b'neutral', b' Knock\r\n', 'RUB'):
            self.assertIsNotNone(parse_message(raw), raw)
        self.assertEqual(parse_message(b'knock'), Message('knock'))
        self.assertFalse(parse_message(b'knock').hb)

    def test_json_string(self):
        self.assertEqual(parse_message(b'"rub"'), Message('rub'))
        self.assertEqual(parse_message(json.dumps('neutral').encode()), Message('neutral'))

    def test_json_object(self):
        self.assertEqual(parse_message(b'{"label":"knock","t":123.4}'), Message('knock', 123.4))
        self.assertEqual(parse_message(b'{"label":"rub"}'), Message('rub'))
        self.assertEqual(parse_message(b'{"label":"rub","t":"x"}'), Message('rub'))
        self.assertEqual(parse_message(b'{"label":"rub","t":true}'), Message('rub'))

    def test_heartbeat_flag_only_for_json_true(self):
        self.assertEqual(parse_message(b'{"label":"neutral","t":1.0,"hb":true}'),
                         Message('neutral', 1.0, hb=True))
        self.assertTrue(parse_message(b'{"label":"KNOCK","hb":true}').hb)
        for raw in (b'{"label":"knock","hb":false}', b'{"label":"knock","hb":1}',
                    b'{"label":"knock","hb":"true"}', b'{"label":"knock","hb":null}',
                    b'{"label":"knock"}', b'knock', b'"knock"'):
            msg = parse_message(raw)
            self.assertIsNotNone(msg, raw)
            self.assertFalse(msg.hb, raw)
        self.assertNotEqual(Message('knock', hb=True), Message('knock'))

    def test_invalid_never_raises(self):
        for raw in (b'', b'   ', b'tap', b'scratch', b'"tap"', b'{"label":"jump"}', b'{}',
                    b'{"t":1}', b'{"label":1}', b'{"hb":true}', b'[1,2]', b'123', b'null',
                    b'\xff\xfe', b'{"label": "knock"', b'[' * 5000, b'k' * 5000, None, 42):
            self.assertIsNone(parse_message(raw), raw if raw is None else repr(raw)[:30])


def run(rule, messages):
    """Feed (label, hb) pairs or bare labels; return the list of executed actions."""
    out = []
    for m in messages:
        label, hb = m if isinstance(m, tuple) else (m, False)
        d = rule.feed(label, heartbeat=hb)
        if d.action:
            out.append(d.action)
    return out


class RuleTests(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(ActionRule().feed('knock').action, NEXT)
        self.assertEqual(ActionRule().feed('rub').action, PREV)
        self.assertIsNone(ActionRule().feed('neutral').action)

    def test_first_message_executes_without_prior_neutral(self):
        # No "starts disarmed": the backend already confirmed the action.
        self.assertEqual(ActionRule().feed('rub').action, PREV)

    def test_two_consecutive_knocks_turn_two_pages(self):
        self.assertEqual(run(ActionRule(), ['knock', 'knock']), [NEXT, NEXT])
        self.assertEqual(run(ActionRule(), ['knock'] * 5), [NEXT] * 5)

    def test_two_consecutive_rubs_go_back_two_pages(self):
        self.assertEqual(run(ActionRule(), ['rub', 'rub']), [PREV, PREV])

    def test_different_actions_without_neutral_between(self):
        self.assertEqual(run(ActionRule(), ['knock', 'rub', 'knock']), [NEXT, PREV, NEXT])

    def test_no_cooldown_or_neutral_hold(self):
        # Timing is not an input at all: the rule has no clock to suppress with.
        self.assertEqual(run(ActionRule(), ['knock', 'knock', 'rub', 'rub']),
                         [NEXT, NEXT, PREV, PREV])

    def test_neutral_never_turns(self):
        r = ActionRule()
        self.assertEqual(run(r, ['neutral', 'neutral', 'knock', 'neutral', 'rub', 'neutral']),
                         [NEXT, PREV])
        self.assertEqual(r.neutrals, 4)
        self.assertIn('no page turn', r.feed('neutral').reason)

    def test_heartbeat_never_turns_whatever_the_label(self):
        r = ActionRule()
        for label in ('knock', 'rub', 'neutral'):
            d = r.feed(label, heartbeat=True)
            self.assertIsNone(d.action, label)
            self.assertIn('heartbeat', d.reason)
            self.assertEqual(r.current, label)        # state is still updated
        self.assertEqual(r.heartbeats, 3)
        self.assertEqual(r.actions, 0)
        # A heartbeat between two real actions does not block or add a turn.
        self.assertEqual(run(ActionRule(), ['knock', ('knock', True), ('knock', True), 'knock']),
                         [NEXT, NEXT])
        self.assertEqual(run(ActionRule(), [('rub', True)] * 20), [])

    def test_unknown_label_ignored(self):
        r = ActionRule()
        self.assertIsNone(r.feed('tap').action)
        self.assertIsNone(r.feed('tap', heartbeat=True).action)
        self.assertEqual((r.actions, r.neutrals, r.heartbeats, r.current), (0, 0, 0, None))

    def test_counts_and_current(self):
        r = ActionRule()
        run(r, ['neutral', 'knock', ('knock', True), 'knock', 'rub', ('neutral', True), 'neutral'])
        self.assertEqual((r.actions, r.neutrals, r.heartbeats), (3, 2, 2))
        self.assertEqual(r.current, 'neutral')

    def test_mock_sequence(self):
        # mock_sender default: neutral, knock, knock, rub, knock with heartbeats between.
        stream = ['neutral'] + [('neutral', True)] * 10
        for a in ('knock', 'knock', 'rub', 'knock'):
            stream += [a] + [(a, True)] * 10
        self.assertEqual(run(ActionRule(), stream), [NEXT, NEXT, PREV, NEXT])


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
            for payload in (b'knock', b'garbage', b'{"label":"rub","t":1.5}', b'"neutral"',
                            b'{"label":"rub","t":2.5,"hb":true}'):
                tx.sendto(payload, listener.address)
            tx.close()
            got = [listener.out.get(timeout=2) for _ in range(5)]
        finally:
            listener.close()
        self.assertEqual([g[0] for g in got], ['msg', 'invalid', 'msg', 'msg', 'msg'])
        self.assertEqual(got[0][1], Message('knock'))
        self.assertEqual(got[2][1], Message('rub', 1.5))
        self.assertEqual(got[4][1], Message('rub', 2.5, hb=True))

    def test_port_in_use(self):
        first = UdpListener('127.0.0.1', 0)
        try:
            with self.assertRaises(PortInUseError) as ctx:
                UdpListener('127.0.0.1', first.address[1])
            self.assertIn('--port', str(ctx.exception))
        finally:
            first.close()


class MockSenderTests(unittest.TestCase):
    """mock_sender sends one datagram per action plus heartbeats; the rule executes each."""

    def test_sequence_and_stress_through_listener(self):
        from mock_sender import Sender, run_sequence, run_stress
        listener = UdpListener('127.0.0.1', 0).start()
        try:
            s = Sender(*listener.address, fmt='mixed', gap_s=0.05, heartbeat_s=0.01, hold_s=0.03)
            run_sequence(s, ['knock', 'knock', 'rub', 'knock', 'rub', 'rub'])
            time.sleep(0.2)
            items = []
            while True:
                try:
                    items.append(listener.out.get(timeout=0.3))
                except queue.Empty:
                    break
            self.assertEqual(len(items), s.sent)
            rule, deck = ActionRule(), SlideDeck(10)
            turns = []
            for item in items:
                self.assertEqual(item[0], 'msg')
                d = rule.feed(item[1].label, heartbeat=item[1].hb)
                if d.action:
                    deck.apply(d.action); turns.append(d.action)
            self.assertEqual(turns, [NEXT, NEXT, PREV, NEXT, PREV, PREV])
            self.assertEqual(deck.index, 0)                  # +1 +1 -1 +1 -1 -1
            self.assertEqual(rule.heartbeats, s.heartbeats)
            self.assertGreater(rule.heartbeats, 0)
            # Like the live decoder: each knock/rub is followed by its own neutral message.
            self.assertEqual([i[1].label for i in items if not i[1].hb],
                             ['neutral'] + [x for a in ('knock', 'knock', 'rub', 'knock', 'rub', 'rub')
                                            for x in (a, 'neutral')])
            s.close()

            s = Sender(*listener.address, fmt='object', gap_s=0.05, heartbeat_s=0.01)
            run_stress(s)
            time.sleep(0.2)
            rule, deck = ActionRule(), SlideDeck(3)
            invalid = turns = 0
            while True:
                try:
                    item = listener.out.get(timeout=0.3)
                except queue.Empty:
                    break
                if item[0] == 'invalid':
                    invalid += 1
                    continue
                d = rule.feed(item[1].label, heartbeat=item[1].hb)
                if d.action and deck.apply(d.action):
                    turns += 1
            self.assertEqual((deck.index, turns, rule.actions, invalid), (0, 4, 7, 5))
            self.assertEqual(rule.heartbeats, s.heartbeats)
            s.close()
        finally:
            listener.close()


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

    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as exc:  # no display / Tk
            self.skipTest(f'Tk unavailable: {exc}')
        self.root.withdraw()

    def make_app(self, log_path=None):
        from slide_demo import BUILTIN_SLIDES, SlideApp

        class FakeListener:
            out = queue.Queue()
            address = ('127.0.0.1', 5005)
            def close(self): pass

        app = SlideApp(self.root, [dict(s) for s in BUILTIN_SLIDES], FakeListener(), None,
                       log_path=log_path)
        t0 = time.monotonic()

        def send(raw, dt=0.0):
            msg = parse_message(raw)
            app.handle(('invalid', raw, t0 + dt) if msg is None else ('msg', msg, raw, t0 + dt))
        return app, send

    def test_handle_messages(self):
        app, send = self.make_app()
        try:
            send(b'{"label":"neutral","t":1,"hb":true}', 0.0)
            send(b'neutral', 0.1)
            self.assertEqual(app.deck.index, 0)
            send(b'\xff', 0.2)
            send(b'knock', 0.3)                             # NEXT -> page 2
            self.assertIn('KNOCK', app.recognized_var.get())
            self.assertIn('NEXT -> page 2', app.slide_var.get())
            send(b'knock', 0.35)                            # second knock, 50 ms later -> page 3
            self.assertEqual(app.deck.index, 2)
            self.assertIn('NEXT -> page 3', app.slide_var.get())
            send(b'{"label":"knock","t":2,"hb":true}', 0.4)  # heartbeat: no turn, display kept
            send(b'{"label":"knock","t":2.1,"hb":true}', 0.5)
            self.assertEqual(app.deck.index, 2)
            self.assertIn('NEXT -> page 3', app.slide_var.get())
            send(b'knock', 0.6)                             # blocked on the last page
            self.assertIn('blocked (already on last page)', app.slide_var.get())
            send(b'rub', 0.65)                              # right after knock, no neutral -> page 2
            self.assertIn('RUB', app.recognized_var.get())
            self.assertIn('PREVIOUS -> page 2', app.slide_var.get())
            send(b'{"label":"rub","t":3.0}', 0.7)            # second rub -> page 1
            self.assertEqual(app.deck.index, 0)
            send(b'{"label":"rub","t":3.5,"hb":true}', 0.8)  # rub heartbeat: still page 1
            send(b'neutral', 0.9)                           # neutral: still page 1
            self.assertEqual(app.deck.index, 0)
            self.assertIn('PREVIOUS -> page 1', app.slide_var.get())
            app.update_status()
            self.assertIn('last valid message:', app.current_var.get())
            self.assertIn('Current label: neutral', app.current_var.get())
            self.assertIn('heartbeats 4', app.state_var.get())
            self.root.update()
            self.assertEqual(app.counts['turns'], 4)
            self.assertEqual(app.counts['invalid'], 1)
            self.assertEqual(app.counts['received'], 11)
            self.assertEqual((app.rule.actions, app.rule.neutrals, app.rule.heartbeats), (5, 2, 4))
            self.assertFalse(any('heartbeat' in h for h in app.history))
        finally:
            app.close()

    def test_log_marks_heartbeats_and_pages(self):
        import csv
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'log.csv'
            app, send = self.make_app(str(path))
            try:
                send(b'knock')
                send(b'{"label":"knock","t":5,"hb":true}')
                send(b'garbage')
                send(b'rub')
            finally:
                app.close()
            rows = list(csv.DictReader(path.open(encoding='utf-8')))
        self.assertEqual([r['kind'] for r in rows], ['msg', 'hb', 'invalid', 'msg'])
        self.assertEqual([r['page'] for r in rows], ['2', '2', '2', '1'])
        self.assertIn('no page turn', rows[1]['decision'])
        self.assertEqual(rows[1]['t'], '5')


if __name__ == '__main__':
    unittest.main()
