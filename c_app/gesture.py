"""Slide action rule: C executes final actions, it does not judge them.

Division of work: the backend (A/B) recognizes and confirms one physical action and
sends ONE final action message for it. This front end only executes:

  * knock -> next page, rub (fingernail-edge scratch on bare wood) -> previous page,
    neutral -> nothing (state display only).
  * Every non-heartbeat action message is one action. Two consecutive knock messages
    turn two pages; two rub messages go back two pages; knock followed directly by
    rub turns forward then back. The label being the same as the previous one is
    never a reason to ignore a message.
  * A heartbeat (`hb=True`, the sender's "current state" repeat) only refreshes the
    state and NEVER turns a page, whatever label it carries.
  * There is no neutral confirmation, no cooldown and no "must pass through neutral
    first" here. The backend has no event id yet, so there is nothing to dedupe on.
  * Page turns clamp at the first/last page; a blocked turn still counts as the action.

Rule, not smoothing: the label stream the GUI shows or that trials are scored on is
untouched.
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


class ActionRule:
    """Stateless mapping from one message to at most one page turn (plus counters)."""

    def __init__(self):
        self.actions = 0        # knock/rub action messages executed (incl. blocked turns)
        self.neutrals = 0       # neutral action messages (no page turn)
        self.heartbeats = 0     # hb messages of any label (no page turn)
        self.current = None     # label of the last valid message, action or heartbeat

    def feed(self, label, heartbeat=False):
        if heartbeat:
            if label in ACTIONS or label == 'neutral':
                self.heartbeats += 1
                self.current = label
                return Decision(None, f'heartbeat {label}: state only, no page turn')
            return Decision(None, f'ignored unknown heartbeat label {label!r}')
        if label == 'neutral':
            self.neutrals += 1
            self.current = label
            return Decision(None, 'neutral: no page turn')
        action = ACTIONS.get(label)
        if action is None:
            return Decision(None, f'ignored unknown label {label!r}')
        self.actions += 1
        self.current = label
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
