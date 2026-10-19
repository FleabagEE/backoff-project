# C: slide demo (knock = next, rub = previous)

A small desktop window that turns pages from the **final live label** shown by
`visualizer.py` (`Prediction: ...`). Labels arrive over UDP on `127.0.0.1:5005`.

| Label | Physical action (current wood v3 definition) | Slide effect |
|---|---|---|
| `knock` | one knuckle knock on the wooden board | next page |
| `rub` | **fingernail edge scratched back and forth on the bare wood** | previous page |
| `neutral` | anything else / quiet | nothing |

Setup and model: `A_wood30x30x6_v3_candidate2` (30 x 30 cm, 6 mm board, bare
wood), `a_models/wood_v3_20261019_135608_v1/`. See `docs/HANDOFF_C.md` and
`MODEL_NOTES.md`.

The slide app only needs the Python standard library (tkinter, socket, threading).
It does not import the capture/model code. Pillow is optional; install it only if
you want JPG slides.

## Run with the live model (on A's computer, with A's hardware)

Do this from the repository root with the `c-integration` branch checked out. The
branch has to be pushed first for A to get it. Use two PowerShell windows.

**Window 1: slide app.** Start it first, so the first label is not missed.

```powershell
uv run python c_app\slide_demo.py --log c_app\live_log.csv
```

**Window 2: live inference.** This is the command from `docs/HANDOFF_C.md`, unchanged:

```powershell
uv run visualizer.py --setup-id A_wood30x30x6_v3_candidate2 --scratch-surface wood --trained-model a_models/wood_v3_20261019_135608_v1/model.joblib --decision-params a_models/wood_v3_20261019_135608_v1/decision_params.json
```

The GUI starts in Infer mode. It sends the first label it computes to UDP, then a
new message every time the label changes, including back to neutral. While fresh
predictions continue, it also repeats the current label as a heartbeat every
0.1 s. The default target is `127.0.0.1:5005`. Add `--slide-udp 127.0.0.1:5006` to use another port,
or `--slide-udp off` to send nothing. If the slide app is not running, nothing
breaks; the datagrams are simply lost.

Check that it works: the bottom line of the slide window shows `received`
increasing when the GUI's Prediction changes.

## How the integration works (and what it does not do)

- The only change to `visualizer.py` is in `update()`, on the line that sets
  `Prediction:`. That same label is passed to `slide_udp.LabelSender`. Nothing
  about the model, features, sampling or band-energy gate changed. log1p and the
  scaler run once, inside the model pipeline.
- **Protocol** (`slide_udp.py`): there are two message types, both JSON, with `t`
  in Unix seconds.
  - **change** `{"label": "knock", "t": 1792450715.095}`: sent for the first label
    after Infer starts or a model loads, and then on every label change. It goes
    out immediately.
  - **heartbeat** `{"label": "neutral", "t": ..., "hb": true}`: the *current*
    label repeated, at most every 0.1 s. It is sent only from the same `update()`
    call that produces a fresh prediction, so heartbeats stop when inference
    stops, the GUI leaves Infer, or audio goes stale (no fresh FFT).

  Silence therefore means "no information", never "still neutral". A heartbeat
  never carries a label the GUI did not show.
- **The slide app's neutral re-arm and cooldown are a front-end trigger rule
  only.** They do not smooth or change the label stream that the GUI shows,
  sends, or that trials are scored on. They make no claim of better recognition
  results in formal trials. They reduce repeated page turns; they cannot
  guarantee exactly one page per physical action, because a wrong or split label
  from the model still reaches them.
- The GUI currently has **no live SPACE trial recorder**. Its Train-mode "trial"
  recording saves FFT frames for offline replay with `trial_replay.py`; it does
  not keep a live label set. If B adds a live recorder, it must read the same
  `self.infer_classes[label]` value that is sent here.

## Run without hardware (mock)

```powershell
cd C:\Users\admin\Desktop\coding\236\backoff-project
python c_app\slide_demo.py
```

In a second window:

```powershell
python c_app\mock_sender.py
```

This sends neutral, then knock, knock, rub, knock, each followed by neutral. You
should see page 1 -> 2 -> 3 -> 2 -> 3.

The window layout:
- **Top left:** the page counter.
- **Top right, large:**
  - `Recognized:` the most recent knock/rub label received, with its time. This
    is shown even when the slide did not move.
  - `Slide:` what the slides did, or why nothing happened, e.g.
    `not turned (waiting for confirmed neutral)` or `not turned (suppressed by cooldown)`.
  - Below that, the current label and the time of the last valid message, with "N s ago".
- **Bottom:** the gate state, counters and recent events.

If `python` is not found, use `py`, or `uv run python` once `uv sync` has been run.

### Options

```powershell
python c_app\slide_demo.py --slides C:\path\to\slides     # PNG/JPG, natural order (1, 2, 10)
python c_app\slide_demo.py --cooldown 1.2                  # default 0.8 s
python c_app\slide_demo.py --neutral-hold 0.8              # confirmed neutral before re-arm, default 0.6 s
python c_app\slide_demo.py --max-gap 0.35                  # max gap inside neutral evidence, default 0.35 s
python c_app\slide_demo.py --port 5006                     # if 5005 is taken
python c_app\slide_demo.py --log c_app\demo_log.csv        # every message + decision
python c_app\slide_demo.py --fullscreen                    # F11 toggles, Esc leaves
```

If the folder has no PNG/JPG files or does not exist, the three built-in demo pages
are shown. For slides from PowerPoint, use **File > Export > PNG**, choose all
slides, and point `--slides` at that folder. Files are sorted in natural order,
so `Slide1.png`, `Slide2.png` and `Slide10.png` stay in sequence without renaming.

Window-local keys are for rehearsal only: **Left/Right** turn pages and **Home**
returns to page 1. These keys work only while the slide window has focus. Space is
deliberately not bound.

### Mock sender

```powershell
python c_app\mock_sender.py knock rub rub knock          # your own sequence
python c_app\mock_sender.py --format object knock        # {"label":"knock","t":...}
python c_app\mock_sender.py --format mixed knock rub     # text / JSON string / object in rotation
python c_app\mock_sender.py --stress                     # invalid + repeats + short-neutral + edges
python c_app\mock_sender.py --interactive                # type k / r / n then Enter; q quits
python c_app\mock_sender.py --port 5006 knock            # match the app's --port
```

The mock sender sends every frame at 21 frames/s. That is a denser version of the
GUI's change + heartbeat stream, and the slide app handles both. For `--stress`,
first press Home in the slide window. The expected result is printed when the run
finishes.

## Message format accepted by the slide app

One UDP datagram per label (UTF-8, case and surrounding whitespace ignored):

```
knock                              plain text
"knock"                            JSON string
{"label": "knock", "t": 123.4}     JSON object; "t" is optional and only logged;
                                   other keys (e.g. "hb") are ignored
```

Any other payload, such as an unknown label, malformed JSON, binary data or more
than 1 KB, is counted as `invalid` and ignored. The app keeps running.

## Page-turn rules (slide app only, front-end anti-repeat)

1. `knock` turns to the next page, `rub` to the previous page. Pages stop at the
   first and last page; a blocked turn shows "already on first/last page".
2. **Re-arm needs confirmed neutral (default 0.6 s, `--neutral-hold`).** Any knock
   or rub disarms the app. It re-arms only when neutral messages keep arriving,
   each within `--max-gap` (default 0.35 s) of the previous message, over at least
   `--neutral-hold` seconds. These messages can be heartbeats or per-frame labels.
   - A single neutral message is not enough.
   - Silence after neutral is not enough.
   - A gap larger than `--max-gap` restarts the count.

   Example: rub@0.1 s, neutral@0.5 s, rub@1.0 s turns **one** page. The app also
   starts disarmed until it has seen a confirmed neutral.
3. **Cooldown (default 0.8 s, `--cooldown`).** Even when re-armed, a knock or rub
   within the cooldown of the previous turn is suppressed (and disarms). The
   model's own `decision_params.json` has `cooldown_s: 0`; this slide cooldown is
   separate and does not change it.
4. Timing uses the arrival time on this computer, not the `t` field. With 0.1 s
   heartbeats, re-arming happens about 0.6–0.7 s after the label returns to
   neutral. In practice the performer must pause for about that long between
   actions for the next one to turn a page.

The window does not take focus after it starts, does not stay on top, does not
inject keystrokes and does not register global hotkeys. Networking runs in a
background thread and passes messages to the UI through a queue. If the port is
already in use, the bottom line turns red with the reason and the app still opens.

## Tests and what was verified

```powershell
python -m unittest discover -s c_app -v          # 24 slide-app tests, stdlib only
uv run python -m unittest -v test_slide_udp      # 11 GUI -> UDP -> slide chain tests
uv run python -m unittest discover               # whole repo (52 tests)
```

The slide-app tests include:
- the reported regression (rub@0.1, neutral@0.5, rub@1.0 turns one page);
- short neutral evidence (0.4 s with heartbeats) not re-arming;
- silence not counting as neutral, and a broken evidence chain restarting;
- the hold and gap settings being configurable, and the cooldown;
- natural sort order (1, 2, 10; Slide1, Slide2, Slide10);
- the window's separate "Recognized" and "Slide" display, including a rub that
  is recognized but not executed.

`test_slide_udp` covers two areas:

- **The sender:**
  - Changes go out immediately.
  - Heartbeats go out at least 0.1 s apart and only repeat the current label.
  - Nothing is sent in Train mode or without fresh frames.
  - It resends after re-entering Infer.
  - Invalid labels are not sent, and a missing receiver does not raise an error.
- **The chain:**
  - The real `App.update()` inference branch runs on fake FFT frames with a
    **simulated prediction sequence**.
  - Every change point of the GUI `Prediction` text is sent at its frame time,
    and every heartbeat matches the label shown on that frame.
  - Through C's real UDP listener and trigger rule, the pages go next, previous,
    next (knock -> rub with no neutral), previous. The second rub, after only
    0.38 s of neutral, is not executed.
  - A further check loads the real wood v3 model and parameter pair, sends
    all-zero frames, and gets `neutral`.

A process-level run used the real slide window and `LabelSender` at a real
21 frames/s, with heartbeats. The `--log` CSV and a window screenshot showed the
expected decisions: the reported regression case gave one previous page, and a
second knock after 0.3 s of neutral was shown as recognized but not turned.

**Not verified:** nothing has run with A's sensor, audio interface or real FFT
frames, and nothing has been measured about latency or recognition accuracy.
See `TEST_PROTOCOL.md`.

## Files

| File | Purpose |
|---|---|
| `slide_demo.py` | Tk window, slide rendering, logging, CLI |
| `gesture.py` | neutral re-arm + cooldown trigger rule, page bounds (no UI) |
| `protocol.py` | UDP payload parsing |
| `udp_listener.py` | background receiver thread, port-in-use detection |
| `mock_sender.py` | sensor-free label stream generator |
| `test_c_app.py` | unit + socket + Tk tests |
| `TEST_PROTOCOL.md` | 20-trial protocol, score sheet, failure log |
| `PITCH.md` | one-minute pitch (English + Chinese) |
| `../slide_udp.py` | sender used by `visualizer.py` (repo root) |
| `../test_slide_udp.py` | GUI -> UDP -> slide chain tests (repo root) |
