"""Forward the GUI's finalized live label to C's slide app over UDP.

Protocol (one JSON datagram each, to 127.0.0.1:5005 by default):
  change     {"label": "<name>", "t": <unix s>}             first label after inference
                                                            (re)starts, then every change
  heartbeat  {"label": "<name>", "t": <unix s>, "hb": true}  the CURRENT label again, at most
                                                            every `heartbeat_s`, and only while
                                                            update() is called, i.e. while the
                                                            GUI produces fresh predictions
When inference stops or audio goes stale, nothing is sent, so the receiver can
tell "label still neutral" (heartbeats keep arriving) from "no information".
Only forwards a label that was already decided; no gating, smoothing or cooldown.
A missing receiver never raises into the GUI loop.
"""
import json
import socket
import time

LABELS = ('neutral', 'knock', 'rub')
DEFAULT_TARGET = '127.0.0.1:5005'
HEARTBEAT_S = 0.1


def parse_target(text):
    """'host:port' -> (host, port); 'off' -> None."""
    if text is None or text.strip().lower() in ('', 'off', 'none'):
        return None
    host, sep, port = text.strip().rpartition(':')
    if not sep or not host or not port.isdigit() or not 0 < int(port) < 65536:
        raise ValueError(f'expected HOST:PORT or off, got {text!r}')
    return host, int(port)


class LabelSender:
    def __init__(self, target=('127.0.0.1', 5005), clock=time.time, monotonic=time.monotonic,
                 heartbeat_s=HEARTBEAT_S):
        self.target = target
        self.clock = clock
        self.monotonic = monotonic
        self.heartbeat_s = heartbeat_s
        self.last = None
        self.last_send = None
        self.sent = 0
        self.heartbeats = 0
        self.errors = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) if target else None

    def reset(self):
        """Call when inference starts or the model changes: next label is sent."""
        self.last = None
        self.last_send = None

    def update(self, label):
        """Call once per fresh final label. Sends a change or a due heartbeat.

        Returns True if a datagram was sent."""
        if self.sock is None or label not in LABELS:
            return False
        now = self.monotonic()
        heartbeat = label == self.last
        if heartbeat and (not self.heartbeat_s or now - self.last_send < self.heartbeat_s):
            return False
        message = {'label': label, 't': round(self.clock(), 3)}
        if heartbeat:
            message['hb'] = True
        try:
            self.sock.sendto(json.dumps(message).encode(), self.target)
        except OSError:
            self.errors += 1
            return False        # keep self.last so the next frame retries
        self.last = label
        self.last_send = now
        self.sent += 1
        self.heartbeats += heartbeat
        return True

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
