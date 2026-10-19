"""Parse UDP label messages from B's live classifier (or mock_sender.py).

Accepted payloads (UTF-8, surrounding whitespace and case ignored):
  plain text     knock
  JSON string    "knock"
  JSON object    {"label": "knock", "t": 123.4}     ("t" optional, numeric)

Anything else returns None; the caller counts it as invalid and keeps running.
"""
import json
import math

LABELS = ('neutral', 'knock', 'rub')   # same finalized label set as B (b_svm_v1.json)
MAX_BYTES = 1024


class Message:
    __slots__ = ('label', 't')

    def __init__(self, label, t=None):
        self.label = label
        self.t = t

    def __eq__(self, other):
        return isinstance(other, Message) and (self.label, self.t) == (other.label, other.t)

    def __repr__(self):
        return f'Message({self.label!r}, t={self.t!r})'


def _label(value):
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    return value if value in LABELS else None


def parse_message(data):
    """bytes or str -> Message, or None if the payload is not a valid label."""
    if isinstance(data, (bytes, bytearray)):
        if len(data) > MAX_BYTES:
            return None
        try:
            data = bytes(data).decode('utf-8')
        except UnicodeDecodeError:
            return None
    if not isinstance(data, str):
        return None
    text = data.strip()
    if not text:
        return None

    label = _label(text)
    if label:
        return Message(label)

    try:
        obj = json.loads(text)
    except (ValueError, RecursionError):
        return None
    if isinstance(obj, str):
        label = _label(obj)
        return Message(label) if label else None
    if isinstance(obj, dict):
        label = _label(obj.get('label'))
        if not label:
            return None
        t = obj.get('t')
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t):
            t = None
        return Message(label, t)
    return None
