# Live SPACE trial mode integration — October 20, 2026

Merged `origin/b-space-trial-mode` at `88b9905` into `a-tuning`, including its
C slide/UDP dependencies. Source branch `b-space-trial-mode`, `c-integration`
and `model-training` are not modified. Audio capture, feature processing,
v1 model and v1 decision parameters are unchanged.

The unfinished event-decision files and T-selection outputs are preserved in
the named Git stash `WIP event decision T selection before requested SPACE mode
integration`; they are not part of this integration or loaded by the GUI.
The scratch-onset/slide-ordering failure remains unresolved; see
[`live_test_20261019.md`](live_test_20261019.md).

## Run from a-tuning

Close earlier collection/inference GUIs first; only one program may capture
the USB Audio CODEC. From `C:\Users\VivoBook\Desktop\backoff`:

```cmd
uv run visualizer.py --setup-id A_wood30x30x6_v3_candidate2 --scratch-surface wood --trained-model a_models/wood_v3_20261019_135608_v1/model.joblib --decision-params a_models/wood_v3_20261019_135608_v1/decision_params.json --slide-udp off
```

This starts Infer with the current v1 window/gate decisions, without slides.
Under **BAKEOFF TRIAL (SPACE = start / stop)**:

1. Select knock_pos, rub_pos, knock_neg or rub_neg.
2. Optionally tick Practice run; practice is logged but not counted.
3. Click **START TRIAL (SPACE)**, or focus the inference window (click its plot)
   and press/release SPACE. Wait for the red RECORDING state before acting.
4. Perform the intended action, wait for its tail, click **STOP TRIAL (SPACE)**
   or press SPACE again to stop.
5. Review Set, PASS/FAIL/INVALID and tally. Undo removes the last trial from
   the tally; Reset tally resets counts. Both are recorded in the log.

SPACE is local to the inference window, not a global hotkey. Typing spaces in
text fields does not start/stop trials. Holding SPACE does not repeatedly toggle.
The keyboard state is also polled per frame to recover missed key/release
callbacks. Hidden text fields cannot block the shortcut. The visible button
provides an equivalent operation when a keyboard callback is unavailable.
There is no automatic eight-second deadline for this live SPACE recorder.
The Train-mode eight-second FFT trial capture is a separate feature.

Positive passes only for {target} or {neutral,target}. Negative passes when the
target is absent. Every fresh final label counts: one wrong transient can fail
a positive trial even when the slide app suppresses that transient. Empty sets,
audio capture faults, mode changes or closing during a trial invalidate it.

The identical label feeds GUI Prediction, UDP sender and trial recorder. The
slide frontend's own cooldown/neutral re-arm does not alter the scored label set.
SPACE logs contain final-label sequences/sets, result, timestamps, model source,
duration, frame count and tally events. They are evaluation records, never
training data; no new model is fitted and no FFT dataset is recorded by SPACE.

## With C's slides

Start the slide receiver FIRST in one terminal:

```cmd
uv run python c_app\slide_demo.py --log "%TEMP%\backoff-space-slides.csv"
```

Then run the inference command above in a second terminal, replacing
`--slide-udp off` with `--slide-udp 127.0.0.1:5005`. Both run from this a-tuning
checkout; a separate C worktree is no longer required to use the merged app.
The default built-in deck has only three pages; page-boundary blocking is not
evidence of a missed model label. Use more slides for longer page-turn tests.

## Logs and verification

Local log: `trial_logs/<timestamp>/trials.jsonl`; the GUI displays its full path.
`trial_logs/` is gitignored and excluded from training. `--trial-log-root` can
select a different local folder. No physical live result was invented here.

Validation on this laptop: 68 repository tests + 24 C slide tests = **92 passed**,
including actual DearPyGui widgets, SPACE repeat/typing protection, scoring,
invalid/practice/undo/reset/log behavior, real model loading and UDP integration.
The C Tk test was rerun with access to the installed Tcl runtime and passed;
the final verification has no skipped tests. Sensor verification awaits A.

Follow-up for A's reported nonresponsive SPACE key: 29 targeted GUI/UDP/fast-take
tests pass, including three new button/polling/hidden-focus regression cases.
This verifies program behavior under controlled input; actual physical keyboard
confirmation is still needed after restarting the updated GUI.
