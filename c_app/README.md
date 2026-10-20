# C: slide demo (knock = next, rub = previous)

A small desktop window that turns pages from **final action messages** received
over UDP on `127.0.0.1:5005`.

**Division of work.** The backend (A/B: model, event decision, sender) recognizes
and confirms one physical action and sends it **once**. The slide app only
executes the result. It does not judge actions: there is no neutral
confirmation, no cooldown and no "must pass through neutral first" rule.

| Label | Physical action (current wood v3 definition) | Slide effect |
|---|---|---|
| `knock` | one knuckle knock on the wooden board | next page |
| `rub` | **fingernail edge scratched back and forth on the bare wood** | previous page |
| `neutral` | anything else / quiet | nothing (state display only) |

Setup and model: `A_wood30x30x6_v3_candidate2` (30 x 30 cm, 6 mm board, bare
wood), `a_models/wood_v3_20261019_135608_v1/`. See `docs/HANDOFF_C.md` and
`MODEL_NOTES.md`.

The slide app only needs the Python standard library (tkinter, socket, threading).
It does not import the capture/model code. Pillow is optional; install it only if
you want JPG slides.

## Message format (what the slide app assumes)

One UDP datagram per message (UTF-8, case and surrounding whitespace ignored):

```
knock                                        plain text         = ONE final action
"knock"                                      JSON string        = ONE final action
{"label": "knock", "t": 1792450715.095}      JSON object        = ONE final action
{"label": "neutral", "t": ..., "hb": true}   state heartbeat    = state only, NEVER a page turn
```

- `t` is optional, numeric and only logged. Timing uses the arrival time on this
  computer; the slide app makes no timing decisions.
- `hb` is a heartbeat only when it is JSON `true`. Missing, `false`, `1` or
  `"true"` all mean a normal action message. Other keys are ignored.
- Any other payload (unknown label, malformed JSON, binary data, more than 1 KB)
  is counted as `invalid` and ignored. The app keeps running.

**Premise: every non-heartbeat action message is one final action.** The backend
protocol has no event id or event message type, so the slide app does not
invent one and does not deduplicate by label or timestamp. Two `knock` messages
in a row are two actions and turn two pages; two `rub` messages go back two
pages; `knock` followed directly by `rub` (no neutral between) turns forward
then back. A message is never ignored just because its label equals the previous
one. If the backend later adds an event id, the slide app should dedupe only
repeats of the same id (and treat a backend restart as a new id space); nothing
else changes.

**What the live backend actually sends (checked against B's commit `db4f9d4`,
merged into this branch).** With `--trained-model` the GUI now defaults to
`--decision event`: `models.EventDecoder` collects the frames of one action
above the energy gate, decides once by majority vote, and `publish_label()`
passes that one final label to the display, to `slide_udp.LabelSender` and to
the SPACE trial set. The sender is unchanged, so on the wire one decided event
looks like this (times are Unix seconds):

```
{"label": "knock", "t": 1792450715.095}                 change: the decided event (ONE per event)
{"label": "knock", "t": 1792450715.195, "hb": true}     heartbeats while the label is held 0.25 s
{"label": "knock", "t": 1792450715.295, "hb": true}
{"label": "neutral", "t": 1792450715.345}               change: hold ended
{"label": "neutral", "t": 1792450715.445, "hb": true}   neutral heartbeats until the next event
```

There is no event id, event type or session id in this protocol, so the slide
app does not deduplicate anything. It relies on the decoder's own structure:
after a decision the label is held 0.25 s and then goes back to neutral, and a
new event cannot close for at least 0.45 s, so two independent knocks always
arrive as two separate `knock` change messages with a `neutral` change between
them. The sender never re-sends the same event: repeating a label only produces
`hb` heartbeats.

Two backend situations are known to break this one-message-per-event property
and are **not** patched over in C:

- `--decision window`, or a model loaded via the **Load Model** dialog, is still
  per-window output. Every label flip is then a change message and the slides
  follow each flip (`test_slide_udp.py` shows knock -> rub without neutral turning
  two pages). Do not drive the slides in that mode.
- `LabelSender.reset()` (mode change, model load) re-sends the current label as a
  change. If that happens inside the 0.25 s hold, C sees the same event twice.
- The sender only sends a change when the label differs from the last one sent.
  If SPACE flushes a second event with the same label while the first event's
  0.25 s hold is still active (second knock starting within about 0.3 s of the
  first decision, SPACE pressed right then), the second event reaches the wire
  only as heartbeats and C does not turn. Reproduced with B's decoder and the
  sender on a fake clock; it needs SPACE inside that window, so it cannot
  happen during a plain demo.

Neither case was patched in C: both are properties of the backend's decoder and
sender, and C deduplicating by label or time would hide real double actions.

## Run without hardware (mock)

```powershell
cd C:\Users\admin\Desktop\coding\236\backoff-project
python c_app\slide_demo.py
```

In a second window:

```powershell
python c_app\mock_sender.py
```

This sends neutral, then knock, knock, rub, knock as **one message each**, each
held with heartbeats for 0.25 s and followed by a neutral message, exactly like
the live event decoder's stream. You should see page 1 -> 2 -> 3 -> 2 -> 3.

The window layout:
- **Top left:** the page counter.
- **Top right, large:**
  - `Recognized:` the most recent knock/rub action message, with its time.
  - `Slide:` what the slides did, e.g. `NEXT -> page 2` or
    `NEXT blocked (already on last page)`.
  - Below that, the current label (last action or heartbeat) and the time of
    the last valid message, with "N s ago".
- **Bottom:** counters (received, actions, neutral, heartbeats, invalid, page
  turns) and the last five events. Heartbeats are counted and logged but not
  listed, so they do not flood the history.

If `python` is not found, use `py`, or `uv run python` once `uv sync` has been run.

### Options

```powershell
python c_app\slide_demo.py --slides C:\path\to\slides     # PNG/JPG, natural order (1, 2, 10)
python c_app\slide_demo.py --port 5006                     # if 5005 is taken
python c_app\slide_demo.py --log c_app\demo_log.csv        # every message + decision
python c_app\slide_demo.py --fullscreen                    # F11 toggles, Esc leaves
```

There are no timing options any more; `--cooldown`, `--neutral-hold` and
`--max-gap` were removed.

If the folder has no PNG/JPG files or does not exist, the three built-in demo pages
are shown. For slides from PowerPoint, use **File > Export > PNG**, choose all
slides, and point `--slides` at that folder. Files are sorted in natural order,
so `Slide1.png`, `Slide2.png` and `Slide10.png` stay in sequence without renaming.

Window-local keys are for rehearsal only: **Left/Right** turn pages and **Home**
returns to page 1. These keys work only while the slide window has focus. Space is
deliberately not bound.

The log CSV has the columns `wall_time, monotonic_s, kind, raw, label, t,
decision, page`, where `kind` is `msg` (action message), `hb` (heartbeat) or
`invalid`.

### Mock sender

The mock sender imitates the backend's final-action output: one datagram per
action, plus `hb` heartbeats of the current label while it waits.

```powershell
python c_app\mock_sender.py knock knock rub rub          # two forward, two back
python c_app\mock_sender.py knock rub                    # forward then back, no neutral between
python c_app\mock_sender.py --format object knock        # {"label":"knock","t":...}
python c_app\mock_sender.py --format mixed knock rub     # text / JSON string / object in rotation
python c_app\mock_sender.py --gap 0.3 knock knock        # 0.3 s between actions (default 1 s)
python c_app\mock_sender.py --heartbeat 0 knock          # no heartbeats between actions
python c_app\mock_sender.py --hold 0 knock               # neutral right after the action (default 0.25 s hold)
python c_app\mock_sender.py --stress                     # invalid + repeats + heartbeats + edges
python c_app\mock_sender.py --interactive                # k / r / n send one action; h = heartbeat; q quits
python c_app\mock_sender.py --port 5006 knock            # match the app's --port
```

For `--stress`, first press Home in the slide window. It checks, in order:
invalid payloads, two knocks in a row (two pages), knock heartbeats (no turn), a
knock blocked on the last page, knock then rub with no neutral between, a replayed
rub heartbeat (no turn), and two rubs in a row (one page, then blocked on the
first page). The expected final state is printed when the run finishes.

## Page-turn rules (slide app only)

1. `knock` turns to the next page, `rub` to the previous page, `neutral` does
   nothing. Pages stop at the first and last page; a blocked turn shows
   "already on first/last page" and still counts as an action.
2. Every non-heartbeat action message is executed, including repeats of the
   same label and different actions with no neutral between.
3. A heartbeat (`"hb": true`) only updates the "current label" line and the
   heartbeat counter. It never turns a page, whatever label it carries.
4. The slide app never waits for neutral and has no cooldown. If one physical
   action turns two pages, the backend sent two action messages; fix it there.

The window does not take focus after it starts, does not stay on top, does not
inject keystrokes and does not register global hotkeys. Networking runs in a
background thread and passes messages to the UI through a queue. If the port is
already in use, the bottom line turns red with the reason and the app still opens.

## Run with the live model (on A's computer, with A's hardware)

This branch (`c-integration`) contains B's event-level decision commit
`db4f9d4`; `a-tuning` does not yet, so run from this branch (or from a branch
that has merged it) and keep the default `--decision event`. Use two windows
from the repository root:

**Window 1: slide app.** Start it first.

```powershell
uv run python c_app\slide_demo.py --log c_app\live_log.csv
```

**Window 2: live inference.** The command from `docs/HANDOFF_C.md`, unchanged:

```powershell
uv run visualizer.py --setup-id A_wood30x30x6_v3_candidate2 --scratch-surface wood --trained-model a_models/wood_v3_20261019_135608_v1/model.joblib --decision-params a_models/wood_v3_20261019_135608_v1/decision_params.json
```

The default target is `127.0.0.1:5005`. Add `--slide-udp 127.0.0.1:5006` to use
another port, or `--slide-udp off` to send nothing. Do not add `--decision window`.
If the slide app is not running, nothing breaks; the datagrams are simply lost.
Check that it works: the bottom line of the slide window shows `received` and
`heartbeats` increasing, and `actions` increasing by one per knock or scratch.

The GUI's **SPACE trial recorder** (B) collects the same final labels that are
sent here: `publish_label()` feeds the display, the UDP sender and the trial set
from one value. The slide app does not change that stream and is not part of
scoring.

## Tests and what was verified

```powershell
python -m unittest discover -s c_app -v          # 25 slide-app tests, stdlib only
uv run python -m unittest -v test_slide_udp      # 11 sender + GUI -> UDP -> slide chain tests
uv run python -m unittest discover               # whole repo
```

The slide-app tests cover:
- two consecutive knocks turn two pages; two consecutive rubs go back two pages;
- knock then rub (and rub then knock) with no neutral between: both executed;
- a heartbeat of any label never turns a page, and a heartbeat between two
  actions neither blocks nor adds a turn;
- neutral never turns a page;
- the first message executes without any prior neutral;
- `hb` parsed only from JSON `true`; plain text, JSON string and object forms;
  invalid payloads (unknown label, malformed JSON, binary, oversized);
- page bounds, natural sort order (1, 2, 10; Slide1, Slide2, Slide10);
- the mock sender's sequence and stress runs received through the real UDP
  listener, including heartbeat counts;
- the Tk window: `Recognized`/`Slide` feedback, counters, history without
  heartbeats, and the CSV log marking `msg` / `hb` / `invalid` rows with pages.

`test_slide_udp.py` keeps the unchanged sender tests (changes go out immediately,
heartbeats at least 0.1 s apart and only of the current label, nothing sent in
Train mode, resend after re-entering Infer, invalid labels dropped, missing
receiver never raises). Its chain tests run the real `App.update()` inference
branch on fake FFT frames through the real UDP sender, C's listener and rule:

- **Event mode (B's live default):** two separate knocks, a scratch, then a knock
  followed by a scratch with the shortest quiet gap, inside a SPACE trial. The
  wire carries exactly one `knock`/`rub` change per decided event, each followed
  by a `neutral` change; datagrams contain only `label`, `t` and `hb`; C turns
  next, next, prev, next, prev; heartbeats turn nothing; the trial's label set
  equals the set of labels C received. A's live scratch #1 pattern (knock
  windows at the scratch onset) sends one `rub` only, and quiet or neutral-majority
  noise sends nothing but heartbeats.
- **Per-window mode:** kept to show that knock -> rub without neutral and
  rub -> short neutral -> rub each turn two pages, which is why that mode must
  not drive the slides.

**Not verified:** nothing has run with A's sensor, audio interface or real FFT
frames. The event-mode sequences are hand-written frame patterns (B's own test
fixtures), not recorded signals. See `TEST_PROTOCOL.md`.

## Files

| File | Purpose |
|---|---|
| `slide_demo.py` | Tk window, slide rendering, logging, CLI |
| `gesture.py` | action -> page mapping (`ActionRule`), page bounds (no UI, no timing) |
| `protocol.py` | UDP payload parsing, including the `hb` flag |
| `udp_listener.py` | background receiver thread, port-in-use detection |
| `mock_sender.py` | sensor-free final-action message generator |
| `test_c_app.py` | unit + socket + Tk tests |
| `TEST_PROTOCOL.md` | 20-trial protocol, score sheet, failure log |
| `PITCH.md` | one-minute pitch (English + Chinese) |
| `../slide_udp.py` | label sender used by `visualizer.py` (repo root, unchanged) |
| `../models.py` | B's `EventDecoder`: the final-action decision (not C's code) |
| `../test_slide_udp.py` | sender + GUI -> UDP -> slide chain tests, event and per-window (repo root) |
