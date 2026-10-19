# Wooden-board v3 provisional model — October 19, 2026

Trained from exactly 75 two-second takes: 25 knock, 25 rub, 25 neutral.
A confirmed that ALL neutral takes are quiet. This model has no adversarial
neutral, untouched holdout, development-trial or fresh-test validation yet.

## Setup and source

- Setup: `A_wood30x30x6_v3_candidate2`, 30 x 30 cm, 6 mm wooden board,
  material unknown, directly on the table. Thin double-sided tape below the
  pickup and retaining tape above; no separate cable strain relief. Bare wood.
- `knock`: knuckle knock; `rub`: fingernail-edge scratch back and forth.
- Only source: `data_sessions/final_v3/20261019_135608_9c907587`.
  Notes describe medium/right/center knocks and normal/right/index scratches.
- All earlier sessions, including incomplete `pilot_wood`, diagnostics, old
  final sessions and the empty earlier final_v3 child, are excluded and retained.
- Capture and feature processing unchanged: WASAPI ch2, 48 kHz int16,
  capture block 480, 2400-sample / 50 ms FFT, 1200 input features.
  Gain A, Windows input 100, enhancements off, phantom power off.
- Earlier absolute-level/contrast acceptance failed; this training does not
  retrospectively change those results or establish durability acceptance.

## Training and validation

Pipeline: frequency cutoff -> log1p -> StandardScaler -> balanced LinearSVC.
Compared 8/12/16 kHz/full band and C={0.0003, 0.001, 0.003, 0.01} using five
stratified folds grouped by take ID. Gate calibration, cleaning, scaler and
model fitting use only each training fold. Selected <=8 kHz, C=0.0003.
The final model fits all 75 takes after model selection.

Primary result: held-out-take event-mean classification **72/75 (96%)**.
This is model-selection CV, not an untouched final test or live window accuracy.
Rows are actual classes; columns are predictions:

| Actual / predicted | neutral | knock | rub |
|---|---:|---:|---:|
| neutral | 25 | 0 | 0 |
| knock | 3 | 22 | 0 |
| rub | 0 | 0 | 25 |

Scratch-to-neutral: 0/25 takes. Event detection found one event in all 25 rub
takes, one in 23 knock takes, none in two knock takes, and none in quiet takes.
The two undetected knocks have peaks about 0.58% FS; the third missed knock
has peak 0.77% FS and an onset near the start (0.031 s). Weak action or timing
is possible; the recordings do not establish the physical cause.
See `take_cv_predictions.csv` for every take, including missing events.

Of 3195 original windows, final fitting retains 2068: neutral 1065, knock 200,
rub 803. Quiet-like and outside-event windows in positive takes are DROPPED,
not fitted with knock/rub labels. Neutral windows are retained. Events use
0.5–8 kHz energy, context -0.2 to +1.5 s, and only observed samples at edges;
there is no synthetic padding. Boundaries are energy-derived, not annotated.

Secondary weak-window accuracy is 87.98% without gate and 90.49% with gate;
scratch-to-neutral is 35/803 (4.36%) energy-active windows. These reference
labels themselves depend on energy, making gated scoring partly circular.
Do not present these as independently measured per-window accuracy.
Whole-take labels incorrectly mark intentional quiet gaps as positive and
likewise are not independent per-window truth. Take labels are the primary metric.

## Artifacts and decision layer

Folder: `a_models/wood_v3_20261019_135608_v1/`.
`model.joblib` and `decision_params.json` must stay paired; the loader checks
their SHA256 and class order: neutral=0, knock=1, rub=2. Reports record source
hashes; original data were read only and are not committed as NPZ files.

The gate is the new quiet windows' P95 of deweighted, temporally smoothed
0.5–8 kHz FFT energy: **469941572.43828094** in proxy energy units, NOT % FS.
Onset is **704912358.6574214**, release equals the gate; refractory 1.7 s,
rearm quiet 0.15 s. The old RMS/peak gate is not used.
Smoothing is provisionally N=1, K_knock=1, K_rub=1, neutral release=1,
cooldown=0. No development-trial temporal search has occurred.

GUI live inference loads the model and applies the WINDOW gate. It does not
apply event aggregation; the 96% event/take CV result is not a live GUI result.
`WoodV3Model.predict_take(X, elapsed_s)` provides event-mean classification
for a complete take. Development trials must compare these approaches before
freezing deployment decisions. No claim of bakeoff PASS is made.

## Run

Close the previous GUI, then run from the repository root:

```powershell
uv run visualizer.py --setup-id A_wood30x30x6_v3_candidate2 --scratch-surface wood --trained-model a_models/wood_v3_20261019_135608_v1/model.joblib --decision-params a_models/wood_v3_20261019_135608_v1/decision_params.json
```

This starts inference; it does not start recording. B can load the same pair:

```python
from wood_v3_model import WoodV3Model
predictor = WoodV3Model("a_models/wood_v3_20261019_135608_v1/model.joblib",
                        "a_models/wood_v3_20261019_135608_v1/decision_params.json")
labels = predictor.predict_windows(X)  # original 1200-feature rows
```

Reproduction (use a NEW output directory to preserve artifacts):

```powershell
uv run python train_wood_v3.py data_sessions/final_v3/20261019_135608_9c907587 --neutral-quiet-confirmed --output a_models/wood_v3_reproduction
uv run python -m unittest discover -v
```

Validation: all 41 tests pass, including source-policy rejection, two-second
event boundaries, model/parameter loading and gate behavior. Pending: genuine
adversarial neutral coverage, independent holdout/trials, temporal tuning, and
fresh test evaluation. One performer, one setup, class-blocked recording order
and limited action variation constrain generalization.
