# B: model, energy gate and how to run inference

Status (October 18, 2026): model **v1** is trained and evaluated. **Knock works and rub does not**,
because the rub signal is too weak (see Results). Gate and label smoothing are implemented in
`models.py` but are **not yet wired into the GUI**.

## What changed

| File | Role | Change |
|---|---|---|
| `models.py` | Library used by the GUI and by training | Added B's preprocessing, a new default model option and the decision layer (below). Capture/FFT code (`get_ear`, `get_audio_features`) is **unchanged**. |
| `train_b_model.py` | **New.** B's training script | Grouped CV selection, final fit, one-time holdout evaluation. Not needed for inference. |
| `b_models/b_svm_v1.model` | **New.** Trained model | Preprocessing + SVM in one sklearn `Pipeline`. |
| `b_models/b_svm_v1.json` | **New.** Model settings | Gate thresholds, smoothing K, CV and holdout results, training data SHA256. |

No raw data, sample rate, FFT size or feature processing was changed.
A's tests pass before and after: `uv run python -m unittest test_collection test_qa_dataset` (13 OK).

### Additions to `models.py`

- `LogSpectrum`: keeps FFT bins up to 8 kHz (first 400 of 1200), then applies `log1p`.
- New model option `"B: log1p <=8kHz + scaler + LinearSVC"`, now `DEFAULT_MODEL_TYPE`.
  `train_model()` builds `LogSpectrum -> StandardScaler -> LinearSVC(C=0.001, class_weight='balanced')`.
  The old `LinearSVC` and `SVC poly` options are still available.
- `preprocess_data()` is **still identity, on purpose**. All preprocessing lives inside the saved
  Pipeline, so the model always takes the raw 1200 features. Training and inference cannot drift
  apart, and the GUI's 1200-feature check on Load Model still passes.
- Decision layer (prediction-label smoothing, separate from the starter's feature smoothing that is
  already inside every FFT frame):
  - `GateConfig` / `calibrate_gate`: a frame is *active* if RMS or peak exceeds its threshold;
    inactive frames are `neutral` and the model is not called.
  - `StabilityConfig` / `Decoder`: the output switches to a label only after K consecutive raw
    frames agree; it returns to `neutral` after 3 neutral frames. Call `reset()` at each trial start.
  - `trial_passes(trial_type, label_set)`: bakeoff rule (`knock+`, `knock-`, `rub+`, `rub-`).

## Saved model

```
b_models/b_svm_v1.model   # load with models.load_model()
b_models/b_svm_v1.json    # gate + smoothing settings; use together with the .model
```

v1 settings (selected by grouped CV on `train.npz`):

| Setting | Value |
|---|---|
| Gate | RMS > 0.3335% FS **or** peak > 1.0162% FS (1.5 x quiet-take P95) |
| Smoothing K | knock 2 frames, rub 6 frames (~21 frames/s); release 3 frames |

`rms_fs`/`peak_fs` are stored as **0..1 FS fractions**, so 0.3335% FS is `0.003335` in code.

## Inference

**Requirement: pull the new `models.py`.** The `.model` file refers to `models.LogSpectrum`;
with the old `models.py` loading fails.

### In the GUI (A's laptop with UM2 connected)

```cmd
git pull
uv run visualizer.py
```

1. Check the device is the **Windows WASAPI USB Audio CODEC** entry and the status shows LIVE.
2. Set Mode to **Infer**.
3. Click **Load Model** and choose `b_models/b_svm_v1.model`.
4. Knock, rub, stay still, and watch Prediction.

Do **not** click Train Model: the GUI's buffer contains the mislabeled holdout takes.

**Expected right now:** the prediction **jumps around while the board is still**. The GUI calls only
preprocessing + SVM; the gate and smoothing from the `.json` are not wired in yet. The SVM was trained
only on gate-active frames, so it never saw silence and has to guess one of three classes. This is not
a model failure and does not represent bakeoff behavior. For now this check confirms only that
`models.py` loads and that hard knocks mostly show `knock`.

### In Python (full pipeline: gate + model + smoothing)

This is the logic that will go into the GUI. It runs once per fresh FFT frame:

```python
import json
from pathlib import Path
import numpy as np
from models import load_model, GateConfig, StabilityConfig, Decoder

model, classes = load_model(Path('b_models/b_svm_v1.model'))
meta = json.loads(Path('b_models/b_svm_v1.json').read_text(encoding='utf-8'))
g, s = meta['gate'], meta['stability']
gate = GateConfig(g['rms_fs'], g['peak_fs'], g['enabled'])
decoder = Decoder(StabilityConfig(k_frames=s['k_frames'], release_frames=s['release_frames'],
                                  default_k=s['default_k']))

def infer_frame(amps, rms_fs, peak_fs):
    """amps: raw 1200 FFT amplitudes; rms_fs/peak_fs: 0..1 FS. Returns the stable label."""
    if gate.is_active(rms_fs, peak_fs):
        raw = classes[int(model.predict(np.asarray([amps]))[0])]
    else:
        raw = 'neutral'
    return decoder.step(raw)
```

In `visualizer.py` the inputs already exist: `amps` from `get_audio_features()`,
`rms = self.ear.pcm_rms / 32768` and `peak = self.ear.pcm_peak / 32768`.
These are the same quantities recorded as `rms_fs`/`peak_fs`.

## Results

Trials were simulated by cutting each take into 5 s segments, each decoded like one SPACE trial.
Takes are continuous 25 s performances, so these numbers compare settings; they are **not** a
bakeoff score prediction.

| Trial type | Grouped CV (train, 6 folds) | Holdout (evaluated once) |
|---|---|---|
| knock+ | 48/50 (96%) | 10/10 (100%) |
| knock- | 113/129 (88%) | 23/25 (92%) |
| rub+ | 11/50 (22%) | **0/10 (0%)** |
| rub- | 127/129 (98%) | 25/25 (100%) |

- Accuracy on gate-active frames: 0.73 (CV), 0.91 (holdout). Without the gate, CV window accuracy was 0.57.
- **Why rub fails:** only 2.4% of holdout rub frames pass the gate (26 of 1067). In training, 6 of 10
  rub takes had ≤6% active frames. The frames that do pass are mostly classified correctly, so the
  limit is signal strength, not the model. Only fast/firm back-and-forth rubs produced enough energy.
- Holdout was evaluated once for v1 (recorded in the `.json`; the script refuses to repeat it).
  **Do not tune on it.** A's QA baseline also evaluated it before.

## Retraining

```cmd
uv run python train_b_model.py                                # CV selection + fit -> b_models/b_svm_v1.*
uv run python train_b_model.py --out b_models/b_svm_v2        # write a new version
uv run python train_b_model.py --out b_models/b_svm_v2 --eval-holdout   # once, after freezing v2
```

Training uses only `handoff/20261017_195725_85cb47b5_review1/train.npz` (corrected split), with
groups by `take_ids`. The gate is calibrated from the `quiet hands off` takes inside each training fold.

## Next steps / requests

1. **A: pick a stronger second gesture.** In the GUI, compare RMS/peak for a firm fingernail scratch,
   scratching with a hard object (coin, pen cap) and a fast firm back-and-forth rub, all next to the
   pickup. Pick the one that most reliably exceeds about 0.33% FS RMS.
2. **Re-record in trial format:** short takes (about 6 s) of still -> one action -> still, from several
   people (A, B, C), including **new holdout takes with Data split set to `holdout`** in the GUI.
3. **B:** wire the gate and smoothing into `visualizer.py` (show the raw and stable labels), then add
   trial mode (SPACE, set, PASS/FAIL tally) and UDP output to C (`localhost:5005`).
