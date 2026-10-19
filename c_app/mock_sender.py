"""Simulate B's finalized label stream without any sensor.

Labels are sent as a continuous frame stream (default 21 frames/s, about B's live
update rate), so one action produces many identical labels in a row, just like the
real classifier. Each action is wrapped as neutral -> action -> neutral. Sending
every frame is a denser form of the live sender's change + 0.1 s heartbeat stream,
so it provides the continuous neutral evidence the slide app needs to re-arm.

    python c_app\\mock_sender.py                      # demo: knock, knock, rub, knock
    python c_app\\mock_sender.py knock rub rub         # your own action sequence
    python c_app\\mock_sender.py --format object knock # {"label": "knock", "t": ...}
    python c_app\\mock_sender.py --stress              # invalid + repeated-label checks
    python c_app\\mock_sender.py --interactive         # type k / r / n, Enter
"""
import argparse
import itertools
import json
import socket
import sys
import time

DURATIONS = dict(neutral=1.0, knock=0.3, rub=1.0)   # rub = ~1 s fingernail-edge scratch on wood
ALIASES = dict(k='knock', r='rub', n='neutral', s='rub', scratch='rub')
FORMATS = ('text', 'json', 'object')


def encode(label, fmt, t0):
    if fmt == 'text':
        return label.encode()
    if fmt == 'json':
        return json.dumps(label).encode()
    return json.dumps({'label': label, 't': round(time.monotonic() - t0, 3)}).encode()


class Sender:
    def __init__(self, host, port, rate, fmt):
        self.addr = (host, port)
        self.period = 1.0 / rate
        self.formats = itertools.cycle(FORMATS) if fmt == 'mixed' else itertools.repeat(fmt)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.t0 = time.monotonic()
        self.sent = 0

    def raw(self, payload):
        self.sock.sendto(payload, self.addr)

    def frames(self, label, seconds):
        n = max(1, round(seconds / self.period))
        print(f'  {label:<8} x{n:<3} ({seconds:.1f}s)', flush=True)
        for _ in range(n):
            self.raw(encode(label, next(self.formats), self.t0))
            self.sent += 1
            time.sleep(self.period)

    def action(self, label, neutral_s=DURATIONS['neutral']):
        self.frames(label, DURATIONS[label])
        self.frames('neutral', neutral_s)


def parse_label(word):
    word = word.strip().lower()
    word = ALIASES.get(word, word)
    if word not in DURATIONS:
        raise ValueError(f'unknown action {word!r}; use knock / rub / neutral (or k / r / n)')
    return word


def run_sequence(s, labels):
    expected = 0
    print('neutral warm-up', flush=True)
    s.frames('neutral', 1.0)
    for label in labels:
        if label == 'neutral':
            s.frames('neutral', DURATIONS['neutral'])
            continue
        expected += 1 if label == 'knock' else -1
        print(f'{label}: expect {"NEXT" if label == "knock" else "PREVIOUS"} page', flush=True)
        s.action(label)
    print(f'done: {s.sent} frames sent. Starting from page 1 the net move is {expected:+d} '
          f'page(s), clamped at the first/last page.')


def run_stress(s):
    print('Start the demo on page 1 of the 3 built-in pages (press Home in the window).')
    s.frames('neutral', 1.0)
    print('1) invalid payloads: window keeps running, "invalid" +5, page stays 1')
    for payload in (b'', b'tap', b'{"label": "jump"}', b'\xff\xfe', b'[1, 2]'):
        s.raw(payload)
    s.frames('neutral', 0.5)
    print('2) knock held 3 s (~63 identical frames): exactly ONE next -> page 2')
    s.frames('knock', 3.0)
    s.frames('neutral', 1.0)
    print('3) knock then rub with no neutral between: ONE next -> page 3, rub ignored')
    s.frames('knock', 0.3)
    s.frames('rub', 1.0)
    s.frames('neutral', 1.0)
    print('4) knock on the last page: blocked, stays page 3')
    s.action('knock')
    print('5) rub, 0.3 s neutral (shorter than the 0.6 s hold), rub again: ONE previous -> page 2')
    s.frames('rub', 0.2)
    s.frames('neutral', 0.3)
    s.frames('rub', 0.4)
    s.frames('neutral', 1.0)
    print('6) rub after the cooldown: ONE previous -> page 1')
    s.action('rub')
    print('7) rub on the first page: blocked, stays page 1')
    s.action('rub')
    print('expected final: page 1, page turns +4, invalid +5; history shows '
          '"waiting for confirmed neutral" and "blocked" entries. (Cooldown is covered by '
          'the unit tests; frame timing here is not precise enough to aim inside it.)')


def run_interactive(s):
    print('Type k (knock), r (rub/scratch) or n (neutral), then Enter. q to quit.')
    s.frames('neutral', 1.0)        # the slide app needs a confirmed neutral before the first action
    for line in sys.stdin:
        word = line.strip().lower()
        if word in ('q', 'quit', 'exit'):
            break
        if not word:
            continue
        try:
            label = parse_label(word)
        except ValueError as exc:
            print(exc)
            continue
        if label == 'neutral':
            s.frames('neutral', DURATIONS['neutral'])
        else:
            s.action(label)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Send mock neutral/knock/rub labels over UDP.')
    ap.add_argument('actions', nargs='*', help='knock / rub / neutral (k / r / n)')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=5005)
    ap.add_argument('--rate', type=float, default=21.0, help='frames per second (default 21)')
    ap.add_argument('--format', choices=FORMATS + ('mixed',), default='text')
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--stress', action='store_true')
    mode.add_argument('--interactive', action='store_true')
    args = ap.parse_args(argv)
    if args.rate <= 0:
        ap.error('--rate must be > 0')
    try:
        labels = [parse_label(a) for a in args.actions] or ['knock', 'knock', 'rub', 'knock']
    except ValueError as exc:
        ap.error(str(exc))

    s = Sender(args.host, args.port, args.rate, args.format)
    print(f'sending to UDP {args.host}:{args.port} at {args.rate:g} frames/s, format={args.format}')
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
    return 0


if __name__ == '__main__':
    sys.exit(main())
