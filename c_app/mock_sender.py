"""Simulate the backend's FINAL ACTION output without any sensor.

The backend recognizes and confirms each physical action and sends it ONCE. So this
sender sends one message per action, not a frame stream. Between actions it can
repeat the current label as a state heartbeat ({"hb": true}), which the slide app
must never treat as a page turn.

    python c_app\\mock_sender.py                      # demo: knock, knock, rub, knock
    python c_app\\mock_sender.py knock rub rub         # your own action sequence
    python c_app\\mock_sender.py --format object knock # {"label": "knock", "t": ...}
    python c_app\\mock_sender.py --stress              # invalid, repeats, heartbeats, edges
    python c_app\\mock_sender.py --interactive         # type k / r / n / h, Enter

Expected slide result for a sequence: every knock turns one page forward, every rub
one page back, in order, clamped at the first/last page. Two knocks in a row turn
two pages; knock then rub with no neutral in between turns forward then back.
"""
import argparse
import itertools
import json
import socket
import sys
import time

ALIASES = dict(k='knock', r='rub', n='neutral', s='rub', scratch='rub')
LABELS = ('neutral', 'knock', 'rub')
FORMATS = ('text', 'json', 'object')


def encode(label, fmt, t0):
    if fmt == 'text':
        return label.encode()
    if fmt == 'json':
        return json.dumps(label).encode()
    return json.dumps({'label': label, 't': round(time.monotonic() - t0, 3)}).encode()


def encode_heartbeat(label, t0):
    """Heartbeats are only defined for the JSON object form."""
    return json.dumps({'label': label, 't': round(time.monotonic() - t0, 3), 'hb': True}).encode()


class Sender:
    def __init__(self, host, port, fmt, gap_s=1.0, heartbeat_s=0.1):
        self.addr = (host, port)
        self.formats = itertools.cycle(FORMATS) if fmt == 'mixed' else itertools.repeat(fmt)
        self.gap_s = gap_s
        self.heartbeat_s = heartbeat_s
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.t0 = time.monotonic()
        self.current = None
        self.sent = 0
        self.heartbeats = 0

    def raw(self, payload):
        self.sock.sendto(payload, self.addr)
        self.sent += 1

    def action(self, label, note=''):
        """ONE final action message (neutral counts as a state message, no turn)."""
        print(f'  send {label:<8}{note}', flush=True)
        self.raw(encode(label, next(self.formats), self.t0))
        self.current = label

    def hold(self, seconds=None):
        """Wait between actions, repeating the current label as heartbeats."""
        seconds = self.gap_s if seconds is None else seconds
        if not self.heartbeat_s or self.current is None:
            time.sleep(seconds)
            return
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            time.sleep(min(self.heartbeat_s, max(0.0, end - time.monotonic())))
            self.raw(encode_heartbeat(self.current, self.t0))
            self.heartbeats += 1

    def close(self):
        self.sock.close()


def parse_label(word):
    word = word.strip().lower()
    word = ALIASES.get(word, word)
    if word not in LABELS:
        raise ValueError(f'unknown action {word!r}; use knock / rub / neutral (or k / r / n)')
    return word


def expected_move(labels):
    return sum(1 if a == 'knock' else -1 if a == 'rub' else 0 for a in labels)


def run_sequence(s, labels):
    s.action('neutral', '   (start state)')
    s.hold()
    for label in labels:
        note = {'knock': '   -> NEXT page', 'rub': '   -> PREVIOUS page'}.get(label, '   (no turn)')
        s.action(label, note)
        s.hold()
    print(f'done: {s.sent} datagrams ({s.heartbeats} heartbeats). Starting from page 1 the '
          f'net move is {expected_move(labels):+d} page(s), clamped at the first/last page.')


def run_stress(s):
    print('Start the demo on page 1 of the 3 built-in pages (press Home in the window).')
    s.action('neutral'); s.hold(0.5)
    print('1) invalid payloads: window keeps running, "invalid" +5, page stays 1')
    for payload in (b'', b'tap', b'{"label": "jump"}', b'\xff\xfe', b'[1, 2]'):
        s.raw(payload)
    s.hold(0.5)
    print('2) knock, knock with no neutral between: TWO next -> page 3')
    s.action('knock'); s.hold(0.3)
    s.action('knock'); s.hold()
    print('3) knock heartbeats for 1 s: NO turn, still page 3')
    s.hold(1.0)
    print('4) knock on the last page: blocked, stays page 3')
    s.action('knock'); s.hold()
    print('5) rub right after knock, no neutral between: knock blocked, rub -> page 2')
    s.action('knock'); s.hold(0.2)
    s.action('rub'); s.hold()
    print('6) neutral, then rub heartbeat replayed: NO turn, still page 2')
    s.action('neutral'); s.hold(0.5)
    s.raw(encode_heartbeat('rub', s.t0)); s.heartbeats += 1
    s.hold(0.5)
    print('7) rub, rub: TWO previous -> page 1 then blocked on the first page')
    s.action('rub'); s.hold(0.3)
    s.action('rub'); s.hold()
    print(f'expected final: page 1, page turns 4 (2 next, 2 previous), actions 7, invalid 5, '
          f'heartbeats {s.heartbeats}; three blocked turns (steps 4, 5 and 7) in the log.')


def run_interactive(s):
    print('Type k (knock), r (rub/scratch), n (neutral) or h (heartbeat of the current '
          'label), then Enter. q to quit. Each k/r/n is ONE final action message.')
    s.action('neutral', '   (start state)')
    for line in sys.stdin:
        word = line.strip().lower()
        if word in ('q', 'quit', 'exit'):
            break
        if not word:
            continue
        if word in ('h', 'hb', 'heartbeat'):
            label = s.current or 'neutral'
            s.raw(encode_heartbeat(label, s.t0)); s.heartbeats += 1
            print(f'  heartbeat {label} (no turn)')
            continue
        try:
            s.action(parse_label(word))
        except ValueError as exc:
            print(exc)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Send mock final-action messages over UDP.')
    ap.add_argument('actions', nargs='*', help='knock / rub / neutral (k / r / n)')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=5005)
    ap.add_argument('--gap', type=float, default=1.0, help='seconds between actions (default 1)')
    ap.add_argument('--heartbeat', type=float, default=0.1,
                    help='seconds between state heartbeats while waiting (default 0.1; 0 = none)')
    ap.add_argument('--format', choices=FORMATS + ('mixed',), default='text',
                    help='action message form (heartbeats are always JSON objects)')
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--stress', action='store_true')
    mode.add_argument('--interactive', action='store_true')
    args = ap.parse_args(argv)
    if args.gap < 0 or args.heartbeat < 0:
        ap.error('--gap and --heartbeat must be >= 0')
    try:
        labels = [parse_label(a) for a in args.actions] or ['knock', 'knock', 'rub', 'knock']
    except ValueError as exc:
        ap.error(str(exc))

    s = Sender(args.host, args.port, args.format, args.gap, args.heartbeat)
    print(f'sending to UDP {args.host}:{args.port}, one message per action, format={args.format}')
    try:
        if args.stress:
            run_stress(s)
        elif args.interactive:
            run_interactive(s)
        else:
            run_sequence(s, labels)
    except KeyboardInterrupt:
        print('stopped')
    except OSError as exc:
        print(f'send failed: {exc}', file=sys.stderr)
        return 1
    finally:
        s.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
