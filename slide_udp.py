"""Forward the GUI's finalized live label to C's slide app over UDP.

Sends {"label": "<name>", "t": <unix seconds>} to 127.0.0.1:5005: the first valid
label after inference (re)starts, then only when the label changes (neutral too).
Only forwards a label that was already decided; it does no gating, smoothing or
cooldown. A missing receiver never raises into the GUI loop.
"""
import json
import socket
import time

LABELS = ('neutral', 'knock', 'rub')
DEFAULT_TARGET = '127.0.0.1:5005'


def parse_target(text):
    """'host:port' -> (host, port); 'off' -> None."""
    if text is None or text.strip().lower() in ('', 'off', 'none'):
        return None
    host, sep, port = text.strip().rpartition(':')
    if not sep or not host or not port.isdigit() or not 0 < int(port) < 65536:
        raise ValueError(f'expected HOST:PORT or off, got {text!r}')
    return host, int(port)


class LabelSender:
    def __init__(self, target=('127.0.0.1', 5005), clock=time.time):
        self.target = target
        self.clock = clock
        self.last = None
        self.sent = 0
        self.errors = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) if target else None

    def reset(self):
        """Call when inference starts or the model changes: next label is sent."""
        self.last = None

    def update(self, label):
        """Send if `label` differs from the last sent one. Returns True if sent."""
        if self.sock is None or label not in LABELS or label == self.last:
            return False
        payload = json.dumps({'label': label, 't': round(self.clock(), 3)}).encode()
        try:
            self.sock.sendto(payload, self.target)
        except OSError:
            self.errors += 1
            return False        # keep self.last so the next frame retries
        self.last = label
        self.sent += 1
        return True

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
