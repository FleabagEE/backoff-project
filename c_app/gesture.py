"""Slide trigger rule: reduce repeated page turns from one physical action.

This is a front-end rule for the slides only. It does not change the label stream
that the GUI shows or that trials are scored on, and it is not model smoothing.

Rules:
  * knock -> next page, rub (fingernail-edge scratch on bare wood) -> previous page.
  * After any knock/rub the gate is DISARMED. It re-arms only after neutral has been
    CONFIRMED for `neutral_hold_s`: neutral messages must keep arriving, each within
    `max_gap_s` of the previous message, spanning at least `neutral_hold_s`.
    A single neutral message, or neutral followed by silence, is NOT enough: missing
    messages are never assumed to mean neutral. The live sender provides this
    evidence with heartbeats (slide_udp.py); per-frame streams work the same way.
  * Even when armed, a trigger within `cooldown_s` of the previous page-turn
    attempt is suppressed (and still disarms).
  * The gate starts disarmed: it needs a confirmed neutral first.
  * Page turns clamp at the first/last page; a blocked turn still counts as the action.

Time is passed in explicitly (monotonic seconds of message arrival) so the logic is testable.
"""

NEXT, PREV = 'next', 'prev'
ACTIONS = {'knock': NEXT, 'rub': PREV}


class Decision:
    __slots__ = ('action', 'reason')

    def __init__(self, action, reason):
        self.action = action    # NEXT, PREV or None
        self.reason = reason    # short human-readable explanation for the UI/log

    def __repr__(self):
        return f'Decision({self.action!r}, {self.reason!r})'


class GestureGate:
    def __init__(self, cooldown_s=0.8, neutral_hold_s=0.6, max_gap_s=0.35):
        if cooldown_s < 0 or neutral_hold_s < 0 or max_gap_s <= 0:
            raise ValueError('cooldown_s, neutral_hold_s must be >= 0 and max_gap_s > 0')
        self.cooldown_s = float(cooldown_s)
        self.neutral_hold_s = float(neutral_hold_s)
        self.max_gap_s = float(max_gap_s)
        self.armed = False
        self.last_trigger = None
        self.last_message = None      # arrival time of the previous valid message
        self.neutral_since = None     # start of the current unbroken neutral evidence

    def in_cooldown(self, now):
        return self.last_trigger is not None and now - self.last_trigger < self.cooldown_s

    def neutral_held(self):
        """Seconds of confirmed continuous neutral up to the last message (0 if none)."""
        if self.neutral_since is None:
            return 0.0
        return max(0.0, self.last_message - self.neutral_since)

    def feed(self, label, now):
        gap_ok = self.last_message is not None and now - self.last_message <= self.max_gap_s
        if label == 'neutral':
            if self.neutral_since is None or not gap_ok:
                self.neutral_since = now          # new or broken evidence chain
            self.last_message = now
            if self.armed:
                return Decision(None, 'neutral')
            held = self.neutral_held()
            if held >= self.neutral_hold_s:
                self.armed = True
                return Decision(None, f'neutral confirmed {held:.2f}s: re-armed')
            return Decision(None, f'neutral {held:.2f}/{self.neutral_hold_s:g}s')

        action = ACTIONS.get(label)
        if action is None:
            return Decision(None, f'ignored unknown label {label!r}')
        self.last_message = now
        self.neutral_since = None
        if not self.armed:
            return Decision(None, f'{label}: waiting for confirmed neutral')
        self.armed = False
        if self.in_cooldown(now):
            return Decision(None, f'{label}: suppressed by cooldown')
        self.last_trigger = now
        return Decision(action, label)


class SlideDeck:
    """Page index only; rendering lives in the UI."""

    def __init__(self, count):
        if count < 1:
            raise ValueError('need at least one slide')
        self.count = count
        self.index = 0

    def apply(self, action):
        """Return True if the page changed."""
        target = self.index + (1 if action == NEXT else -1 if action == PREV else 0)
        target = max(0, min(self.count - 1, target))
        changed = target != self.index
        self.index = target
        return changed
