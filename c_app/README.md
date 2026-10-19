# C: slide demo (knock = next, rub = previous)

A small desktop window that turns pages from the **finalized labels** produced by
B's live classifier. Labels arrive over UDP on `127.0.0.1:5005`.

| Label | Physical action (current v2 definition) | Slide effect |
|---|---|---|
| `knock` | knuckle knock on the KNOCK pad | next page |
| `rub` | **fingernail scratch back and forth on the paper pad** (not fingertip rubbing) | previous page |
| `neutral` | anything else / quiet | nothing |

The app only needs the Python standard library (tkinter, socket, threading). It does
not import the capture/model code and does not need `uv`, PyAudio, sounddevice,
numpy or scikit-learn. Pillow is optional; install it only if you want JPG slides.

## Run it (Windows PowerShell)

Open **two** PowerShell windows. In each one, change to the repository root:

```powershell
cd C:\Users\admin\Desktop\coding\236\backoff-project
```

Window 1 starts the slide app:

```powershell
python c_app\slide_demo.py
```

Window 2 sends a mock label stream (neutral, then knock, knock, rub, knock, each followed by neutral):

```powershell
python c_app\mock_sender.py
```

You should see page 1 -> 2 -> 3 -> 2 -> 3. The page counter is at the top left,
the last action at the top right, and the gate state, counters and recent events
at the bottom.

If `python` opens the Microsoft Store or is not found, replace `python` with `py`.
Python 3.10 or newer with tkinter is required (the standard python.org installer includes it).

### Options

```powershell
python c_app\slide_demo.py --slides C:\path\to\slides     # PNG/JPG sorted by file name
python c_app\slide_demo.py --cooldown 1.2                  # default 0.8 s
python c_app\slide_demo.py --port 5006                     # if 5005 is taken
python c_app\slide_demo.py --log c_app\demo_log.csv        # every message + decision
python c_app\slide_demo.py --fullscreen                    # F11 toggles, Esc leaves
```

If the folder has no PNG/JPG files or does not exist, the three built-in demo pages
are shown. For slides from PowerPoint, use **File > Export > PNG**, choose all
slides, and point `--slides` at that folder. Exported names such as `Slide1.png`
and `Slide10.png` sort by name, so rename them to `01.png`, `02.png` and so on if
the deck has 10 or more slides.

Window-local keys are for rehearsal only: **Left/Right** turn pages and **Home**
returns to page 1. These keys work only while the slide window has focus. Space is
deliberately not bound.

### Mock sender

```powershell
python c_app\mock_sender.py knock rub rub knock          # your own sequence
python c_app\mock_sender.py --format object knock        # {"label":"knock","t":...}
python c_app\mock_sender.py --format mixed knock rub     # text / JSON string / object in rotation
python c_app\mock_sender.py --stress                     # invalid + repeated-label + cooldown + edges
python c_app\mock_sender.py --interactive                # type k / r / n then Enter; q quits
python c_app\mock_sender.py --port 5006 knock            # match the app's --port
```

The sender imitates the real stream. It sends one label per frame at 21 frames/s,
so a knock lasts about 6 identical frames and a scratch about 21. Each action is
wrapped as neutral -> action -> neutral. For `--stress`, first press Home in the
slide window. The expected result is printed when the run finishes.

## Message format

One UDP datagram per label (UTF-8, case and surrounding whitespace ignored):

```
knock                              plain text
"knock"                            JSON string
{"label": "knock", "t": 123.4}     JSON object; "t" is optional and only logged
```

Any other payload, such as an unknown label, malformed JSON, binary data or more
than 1 KB, is counted as `invalid` and ignored. The app keeps running.

## Page-turn rules

1. `knock` turns to the next page, `rub` to the previous page. Pages stop at the
   first and last page; a blocked turn shows "already on first/last page".
2. **One action, one page.** Any knock or rub disarms the app until a `neutral`
   label arrives. A stream like `knock knock knock ...` turns one page. So does a
   knock that becomes rub without neutral in between.
3. **Cooldown (default 0.8 s, `--cooldown`).** Once re-armed, a knock or rub within
   the cooldown of the previous turn is suppressed. It also disarms, so it cannot
   fire later on its own.
4. Timing uses the arrival time on this computer (`time.monotonic()`), not the `t` field.

The window does not take focus after it starts, does not stay on top, does not
inject keystrokes and does not register global hotkeys. Networking runs in a
background thread and passes messages to the UI through a queue, so a burst of
packets cannot freeze the window. If the port is already in use, the bottom line
turns red with the reason. The app still opens so you can rehearse with the arrow
keys. Run it again with a different `--port`, or close the other copy.

## For B: sending labels from the live pipeline

Send the **same finalized label** (after your energy gate and smoothing) that goes
into the SPACE trial set, one per frame. Repeats are fine; the app removes them.
B's code (not this folder) would add something like:

```python
import json, socket, time
_slide_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_slide_label(label):          # label in {"neutral", "knock", "rub"}
    try:
        _slide_sock.sendto(json.dumps({"label": label, "t": time.monotonic()}).encode(),
                           ("127.0.0.1", 5005))
    except OSError:
        pass                          # the slide app may not be running
```

## Tests and what was verified

```powershell
python -m unittest discover -s c_app -v
```

There are 16 standard-library tests. They cover:

- **Message parsing:** the three accepted formats, plus garbage, unknown labels, bad bytes and oversize payloads.
- **Repeat suppression:** 63 identical knock frames give one turn; knock -> rub needs a neutral in between.
- **Cooldown:** a second action inside 0.8 s is suppressed; exactly 0.8 s is allowed; the cooldown is configurable.
- **Page edges:** first page, last page and a one-slide deck.
- **Real UDP socket:** messages are received and invalid ones are reported.
- **Port in use:** a clear error is raised.
- **Slide folder:** files are read and sorted; missing or empty folders fall back to the built-in pages.
- **Window:** the Tk window handles messages, including invalid ones.

An end-to-end check on Windows 11 with Python 3.14 ran the real window with
`mock_sender.py --stress` and `--format mixed knock rub`, and logged results with
`--log`. The CSV showed the expected decisions: 5 invalid messages ignored, 4
turns, the cooldown suppression, both edge blocks, and every format parsed. A
second app copy on the same port showed the "already in use" warning.

**Not verified:** the app has not run with the real sensor or B's live classifier.
B's live UDP sender does not exist yet. See `TEST_PROTOCOL.md` for the hardware trials.

## Files

| File | Purpose |
|---|---|
| `slide_demo.py` | Tk window, slide rendering, logging, CLI |
| `gesture.py` | neutral re-arm + cooldown gate, page bounds (no UI) |
| `protocol.py` | UDP payload parsing |
| `udp_listener.py` | background receiver thread, port-in-use detection |
| `mock_sender.py` | sensor-free label stream generator |
| `test_c_app.py` | unit + socket + Tk tests |
| `TEST_PROTOCOL.md` | 20-trial protocol, score sheet, failure log |
| `PITCH.md` | one-minute pitch (English + Chinese) |
