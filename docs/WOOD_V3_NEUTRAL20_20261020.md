# Wood v3 neutral-interference model v2 — October 20, 2026

Trained locally on integration branch `a-b-event-integration-20261020`.
Artifacts: `a_models/wood_v3_20261020_v2/model.joblib` and paired
`decision_params.json`. v1, raw recordings, B/C source branches and hardware
were preserved. The GUI currently open for recording has NOT been switched to v2.

## Data and unchanged processing

- Original session `20261019_135608_9c907587`: knock25 / rub25 / quiet neutral25.
- New session `20261020_185237_766164bf`: neutral20, ten interference actions x2.
- All95 are valid train/take, performer A, approximately2s. NPZ hashes are in the
  training report and were checked again after training; no raw files rewritten.
- WASAPI ch2 / 48kHz / 50ms2400-sample FFT / full1200 saved features unchanged.
- Fixed v1 pipeline: <=8kHz -> log1p -> StandardScaler -> balanced LinearSVC,
  C=.0003. No new hyperparameter search. All neutral windows retained; quiet-like
  and outside-event positive windows DROPPED, never labelled knock/rub.
- Final gate is exactly v1: 469941572.43828094, calibrated from original25 QUIET
  takes only. Interference never calibrates the quiet threshold. Each CV fold
  fits its gate, scaler and classifier using training takes only.
- B EventDecoder unchanged: trigger/vote=gate, max1s, quiet end.3s, min2 votes,
  hold.25s, rearm quiet.15s; majority including neutral, mean-score tie break.

## Five-fold take-grouped CV

Each take appears in exactly one test fold. Entire take IDs stay together.
These are development results from one performer/setup, not fresh live tests.

Mean-score whole-take accuracy: **91/95 (95.8%)**, macroF1 .9537.
Rows=true, columns=predicted:

| True / predicted | neutral | knock | rub |
|---|---:|---:|---:|
| neutral |45|0|0|
| knock |3|21|1|
| rub |0|0|25|

The CURRENT B majority-event decoder instead passes **87/95 (91.6%)** under
the GUI trial-set rule: neutral45/45, knock17/25, rub25/25. One passing knock
emits knock twice; only16/25 knocks and25/25 scratches emit exactly one correct
action. Do not equate a trial-set pass with exactly one slide turn.

Scratch->neutral: 0/25 in both metrics; see decoder confusion below for knock
misses/wrong outputs. Per-window accuracy is not reported because these2s takes
contain quiet gaps without human window annotations. Take labels cannot label
every window correctly.

Decoder replay starts fresh for each2s take and flushes pending votes at take
end, exactly like GUI trial-stop. It does NOT establish uninterrupted streaming
latency, rearming, independence of neighboring actions or slide behavior.

| B decoder: true / emitted set | none (neutral) | knock only | rub only | mixed K+R |
|---|---:|---:|---:|---:|
| neutral | 45 | 0 | 0 | 0 |
| knock | 7 | 17 | 1 | 0 |
| rub | 0 | 0 | 25 | 0 |

## Interference comparison

Old v1 model on NEW20:17/20 takes emitted false knock; v2 held-out CV:0/20
false action takes. This is a development comparison: v1 saw none of these
interference takes, while each v2 fold trains on the other interference takes.
Only two takes per action; zero observed errors does not prove robustness.
Whole-take mean scoring called ALL20 neutral even for v1, demonstrating why
its offline accuracy must not substitute for the live event decoder.

| Interference | v1 false-trigger takes | v2 CV false-trigger takes |
|---|---:|---:|
| palm_slap | 2/2 | 0/2 |
| fingertip_tap | 2/2 | 0/2 |
| board_flick | 2/2 | 0/2 |
| phone_place | 1/2 | 0/2 |
| phone_lift | 2/2 | 0/2 |
| cup_place | 2/2 | 0/2 |
| hand_rest | 2/2 | 0/2 |
| table_tap | 2/2 | 0/2 |
| typing | 2/2 | 0/2 |
| object_drag | 0/2 | 0/2 |

Offline onset counts (counts of takes by detected-event count, expected1 per positive take): `{"knock": {"0": 2, "1": 23}, "rub": {"1": 25}}`. These training segmentation onsets differ from B live decoder boundaries.

Fit windows by class: `{"neutral": 1915, "rub": 803, "knock": 200}`.

## Load v2 for a fresh live check (CMD)

Close the collection GUI first; only one process may open the sensor. To test
classification first, run in a terminal:

```cmd
cd /d C:\Users\VivoBook\Desktop\backoff-event-integration
..\backoff\.venv\Scripts\python.exe visualizer.py --setup-id A_wood30x30x6_v3_candidate2 --scratch-surface wood --trained-model a_models/wood_v3_20261020_v2/model.joblib --decision-params a_models/wood_v3_20261020_v2/decision_params.json --decision event --slide-udp off
```

For slides, start `c_app\slide_demo.py` first and replace `--slide-udp off` with
`--slide-udp 127.0.0.1:5005`. Current C receiver needs no change; it accepts event
labels and ignores heartbeats. Do not use the old per-window runtime.

The existing GUI banner still says adversarial trials are not validated; this
is appropriate: interference is now TRAINED, but fresh adversarial trials remain
pending. No tuning of the decision logic was performed to hide knock misses.

Recommended next step: fresh10 knocks,10 scratches and stillness30s, followed
by interference actions, checking both missed actions and duplicate slide turns.
Pay special attention to light knocks. Do not claim final acceptance yet.

## Reproduce

```cmd
..\backoff\.venv\Scripts\python.exe train_wood_v3_neutral20.py --data-root C:\Users\VivoBook\Desktop\backoff\data_sessions\final_v3 --output a_models/wood_v3_neutral20_reproduction --v1 a_models/wood_v3_20261019_135608_v1
```

Output must be a NEW folder; existing model artifacts are never overwritten.
New five data/gate/decoder regression tests and21 existing relevant tests passed
(26 total). Saved model/params hash and1200-input compatibility verified on all95
takes without opening the audio device. The full report contains per-take folds,
predictions, emitted labels, decoder events and source hashes. No NPZ is published.
