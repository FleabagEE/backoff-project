# B: train from A's saved FFT sessions

## Capture profile

Run `uv run visualizer.py`. The repaired capture uses UM2 **INST 2**, USB Audio
CODEC / WASAPI, stereo int16 at **48000 Hz**, selects physical **channel 2**, then
feeds the existing mono FFT buffer. Capture block is 480 frames/channel. FFT remains
**50 ms / 2400 samples**; no classifier or preprocessing algorithm was changed.
Windows input level is 100 and **audio enhancements OFF**.

The starter's old mono PyAudio path captured only ch1/noise for this device even
though sounddevice mono included INST 2. Do not reuse old mono recordings. Exact
rate/channel selection now fails explicitly instead of silently falling back to
another device, backend or sample scale. Device indices may change after USB reconnect.

The old one-shot GUI callback chain is replaced with the documented main render
loop and manual widget callbacks. FFT requests target 30/s; only newly computed
features are recorded/predicted. Actual rate depends on render/compute load and is
represented by per-frame timestamps. Existing overlapping 50 ms windows, feature
weighting and temporal smoothing remain; train and infer with this same pipeline.

## Loading a session

A hands over an entire `data_sessions/<session>/` directory. Export is created by
the GUI button, normal close, or rebuilt after restart with:

```cmd
uv run collection.py "data_sessions\YOUR_SESSION_FOLDER"
```

```python
import json
import numpy as np
from models import preprocess_data, train_model, save_model
from pathlib import Path

with np.load('data_sessions/YOUR_SESSION_FOLDER/dataset.npz', allow_pickle=False) as d:
    X = d['X'].copy()                     # float32, (N, 1200), un-preprocessed FFT amplitudes
    y = d['y'].copy()                     # int64, index into class_names
    class_names = d['class_names'].tolist()
    groups = d['take_ids'].copy()         # one ID per frame; keep takes together in splits
    elapsed_s = d['elapsed_s'].copy()     # elapsed wall time within each take
    rms_fs = d['rms_fs'].copy()           # unsmoothed 50 ms selected-channel PCM RMS / 32768
    peak_fs = d['peak_fs'].copy()         # unsmoothed 50 ms selected-channel PCM peak / 32768
    config = json.loads(str(d['config_json']))
    takes = json.loads(str(d['takes_json']))

assert X.shape[1] == 1200 and config['sample_rate'] == 48000
assert config['selected_channel_1_based'] == 2
assert {'neutral', 'knock', 'rub'} <= set(class_names)
# Split by performer/take FIRST; do not use all X for both training and validation.
# train_rows is determined by your group/performer split.
# model, names = train_model(preprocess_data(X[train_rows]), y[train_rows], class_names)
# save_model(model, names, Path('vibration.model'))
```

`config.json` includes exact source hashes, package versions and setup references.
Individual `take_*.npz` archives contain the same feature arrays, level measurements,
`metadata_json` and `config_json`; `takes.csv` logs performer, variation, duration,
count, validity and filename. `SETUP_snapshot.md` captures the setup documentation
at first recording. Actual knob/mount photos and outstanding physical measurements
must still be supplied by A. No WAV/raw audio is saved.

There are 1200 FULL FFT features at this rate/window, **not 512 grouped bins**.
FFT drops DC; actual retained frequencies are 20, 40, ..., 24000 Hz. The inherited
plot x coordinates start at 0 (a one-bin labeling offset); that existing feature/
plot convention was not changed to avoid altering the calibrated signal pipeline.
`preprocess_data()` remains identity. Fitted normalization must be trained only on
training data and reused unchanged at inference; persist its fitted parameters.

## Data quality and splitting

- Adjacent windows overlap; cached frames are not duplicated. Per-frame time is
  GUI processing time, not a sample-accurate hardware timestamp.
- Give takes/performers separate train/validation/test groups. `takes_json` maps IDs
  to performers/variation; `takes.csv` provides the same context. Randomly splitting
  adjacent frames will overestimate accuracy.
- When combining sessions, validate channel/rate/FFT/dtype/pipeline and physical
  setup compatibility. Map label NAMES into one common list before concatenating y;
  each archive has its own class-index ordering.
- `*.excluded.npz` takes are retained for audit/recovery but omitted by export.
  GUI Clear data excludes every saved take of that class in the current session.
  To exclude one mislabeled take manually, close GUI, rename `take_x.npz` to
  `take_x.excluded.npz` and rerun `collection.py`. Its filename is authoritative;
  `takes.csv` is the GUI-generated log and may still reflect a manual exclusion.
- Each take is saved on stop/25 s timeout. A normal exit saves partial active takes;
  a hard kill can lose the active take. Previously saved archives remain recoverable.
- Energy-gate calibration can use `rms_fs` and `peak_fs` (0..1 FS, NOT percentages).
  Features include temporal smoothing while these levels are from the current PCM
  window; handle onset/release accordingly. No gate or class smoothing was added.
- Quiet RMS was ~0.114% FS (0.00114 FS); mounted rub was variable and about 8.8 dB
  above quiet by one segment-median comparison. Treat as a calibration reference,
  not a final threshold. Strong-knock peak reference ~32.135% FS.

## Remaining software owned by B/C

Train/validate neutral, knock and rub; add energy gate, consecutive agreement/
temporal decisions, SPACE trial start/stop and set accumulation, slide next/previous
actions/cooldown, and official positive/negative trial evaluation. All downstream
consumers must use the SAME finalized output label, consistent with course rules.
A gate used only for slides cannot remove stray labels already inserted in a trial set.
Model loading alone does not establish physical/profile compatibility; verify config.

## Verification completed for collection changes

- `uv run python -m unittest -v test_collection`: channel-2 selection into real FFT,
  fixed rate/feature shape, recoverable non-pickle exports, exclusions, atomic write
  failure and idempotent retry.
- Real UM2 and Dear PyGui: continuous render/FFT updates; timed take auto-stop;
  manual stop/autosave; export and load `(N,1200)` arrays; Clear then re-export;
  normal cleanup. Test recordings were temporary, not training data.

Before final collection, A still confirms the displayed live PCM/FFT responds to
actual board knocks/rubs with this repaired app. Software verification does not
establish classification performance or official bakeoff trial success.
