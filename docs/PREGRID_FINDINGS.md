# Scratch pre-grid diagnostics — October 19, 2026

Branch: `a-tuning`, based on B's `model-training` commit `f6aa2bd`.
This is a preliminary training-only comparison. No holdout was evaluated,
no full parameter grid was run, and no capture or FFT processing was changed.

## Frequency cutoff

Five-fold GroupKFold by take ID, identical folds across the four cutoffs within
each neutral-data policy. Pipeline: existing FFT features -> cutoff -> log1p ->
StandardScaler -> balanced LinearSVC, C=0.001. Scaler/model fitting and quiet-P95
positive-window cleaning occur inside each training fold. All neutral rows are
retained; only quiet-like positive training rows are removed. Test rows are not
cleaned. These scores therefore describe all recorded test windows, including
gaps in action-labelled takes; they are not event/trial pass rates.

Sources: old final session `20261017_195725_85cb47b5`, corrected train knock and
neutral only; ten accepted scratch train takes from
`final_v2/20261018_101351_e6b598a9`, applying `final_v2_exclusions.csv`.
No old fingertip-rub takes enter fitting or evaluation. Counts with drag included:
16 neutral, 10 knock, 10 scratch takes.

| Cutoff | Macro F1, drag included | Balanced accuracy | Scratch recall | Macro F1, drag excluded |
|---|---:|---:|---:|---:|
| 8 kHz | 73.86% | 72.93% | 85.88% | 71.83% |
| 12 kHz | 73.85% | 72.80% | 84.98% | 71.71% |
| 16 kHz | 73.72% | 72.62% | 84.34% | 71.44% |
| Full band | 72.94% | 71.89% | 83.48% | 70.80% |

8 kHz is the provisional leader, essentially tied with 12 kHz. Higher cutoffs
have not improved these training CV scores. This does not establish where raw
scratch energy lies: these are weighted/smoothed FFT features. Including drag
has the higher score in this comparison, but excluding takes also changes the
fold composition/evaluation population, so this is not a controlled causal
estimate. Keep both policies for subsequent trial evaluation.

## B's existing energy gate

B activates a window if RMS > **0.333507% FS OR peak > 1.016235% FS**.
Failing either condition alone does not mean rejection; both must fail.

| Scratch data | Windows | Fail RMS | Fail peak | Rejected by OR gate |
|---|---:|---:|---:|---:|
| All ten training takes | 5,332 | 95.39% | 90.96% | 90.74% |
| Two light training takes | 1,065 | 97.37% | 92.30% | 92.21% |
| Actual rub_pos trials | Not recorded | Pending | Pending | Pending |

Across training scratch windows median RMS is 0.167154% FS and P10 is
0.120764% FS. This is substantially weaker than the separate 10-second light
feasibility run (median 0.4269% FS). The files alone cannot explain whether
pressure, pauses, or another collection difference caused this discrepancy.
No recordings have been changed or discarded because of it.

The 8 kHz model's all-window CV accuracy falls from 76.51% to 52.66% when
the fixed B gate is applied. It is unsuitable to carry that gate forward
without testing lower thresholds. The later grid must include RMS thresholds
0.12%, 0.15%, 0.20%, 0.25%, and B's 0.333507% FS, along with quiet-calibrated
peak thresholds and a gate-disabled comparison. Select using development
trials, including neutral onset/tail; never use holdout to select a gate.

Training snapshots use overlapping 50 ms PCM windows at the saved feature-update
cadence (about 21/s); feasibility windows were non-overlapping. Counts here
are saved-window fractions, not independent observations or trial counts.

## Knock K and actual trials

No actual knock_pos or rub_pos trial recordings exist yet. Consecutive gate-active
windows for a single knock, cutoff performance on trials, and scratch-trial gate
rejection rates remain unmeasured. Do not substitute continuous-knock training
takes or artificial slices for single-action trials. Include knock K=1 and K=2
in the later search; gate-active runs alone are insufficient if raw predicted
labels disagree. Report action interval (2–3 s), surrounding decay, and full-trial
false activations separately when actual recordings exist.

Two confirmed scratch holdout takes are also still missing. Finish them first,
then collect the requested twenty development trials, one at a time. After
tuning, record eight fresh trials for the untouched test. Full-grid tuning
remains pending until these three diagnostics can include actual trials.

Reproduce the current diagnostics with a new output directory:

```cmd
uv run python pregrid_diagnostics.py --scratch-session data_sessions/final_v2/20261018_101351_e6b598a9 --output handoff/NEW_PREGRID_RUN
```

Add repeated `--trial-session ACTUAL_FOLDER` arguments once development trials
exist. Never pass the fresh final test. Machine-readable current results and
fold membership are in `handoff/a_tuning_pregrid_20261019/diagnostics.json`;
per-take gate fractions are in the adjacent `scratch_gate_by_take.csv`.
