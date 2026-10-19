"""One action -> at most one page turn.

Rules:
  * knock -> next page, rub (fingernail scratch on paper) -> previous page.
  * After any knock/rub the controller is DISARMED until a neutral label arrives.
    A continuous stream such as knock, knock, knock ... or a knock -> rub switch
    without neutral in between therefore turns at most one page.
  * Even when armed, a trigger within `cooldown_s` of the previous page-turn
    attempt is suppressed (and still disarms, so it cannot fire later on its own).
  * Page turns clamp at the first/last page; a blocked turn still counts as the action.

Time is passed in explicitly (monotonic seconds) so the logic is testable.
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
    def __init__(self, cooldown_s=0.8):
        if cooldown_s < 0:
            raise ValueError('cooldown_s must be >= 0')
        self.cooldown_s = float(cooldown_s)
        self.armed = True
        self.last_trigger = None

    def in_cooldown(self, now):
        return self.last_trigger is not None and now - self.last_trigger < self.cooldown_s

    def feed(self, label, now):
        if label == 'neutral':
            was_armed, self.armed = self.armed, True
            return Decision(None, 'neutral' if was_armed else 'neutral: re-armed')
        action = ACTIONS.get(label)
        if action is None:
            return Decision(None, f'ignored unknown label {label!r}')
        if not self.armed:
            return Decision(None, f'{label}: waiting for neutral')
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
