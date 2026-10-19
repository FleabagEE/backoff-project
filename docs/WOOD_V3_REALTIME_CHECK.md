# Wooden-board v3 preliminary inference checks — 2026-10-19

Frozen model/parameters: `a_models/wood_v3_20261019_135608_v1/`.
No retraining, gate changes, hardware changes or capture/feature changes were
made during these checks. The results below are preliminary, not an untouched
formal test suite or a measured deployment success rate.

## Saved neutral interference replay

One two-second take was recorded in the isolated session
`data_sessions/wood_v3_neutral_test/20261019_143751_ca9cb6af`:
`take_66bb9965eab849969ddfb424565f832b`, notes `neutral_test_palm_slap_01`.
A reports a single palm slap. The raw metadata accidentally says train, not
holdout. The recording is explicitly EVALUATION ONLY by source-session
selection, excluded from training; original metadata/data have not been edited.

Frozen-model offline replay: 42/42 windows neutral, zero non-neutral outputs.
The event detector detected no event; the event result therefore defaults to
neutral. This shows no false trigger on this recording, not successful event
detection of the slap. Machine-readable report:
`handoff/wood_v3_neutral_test_20261019/take_66bb9965eab849969ddfb424565f832b_replay.json`.
The requested next fingertip-tap recording has NOT been confirmed received.

## Live GUI observations

The GUI loaded the model and band gate and entered Infer. A supplied a
screenshot showing live capture status 0 and Prediction: neutral at rest,
then a screenshot showing Prediction: rub during fingernail scratch.
Knock predictions initially flashed too briefly for A to read confidently.
After further manual checks, A reported all tested actions/interference were
recognized successfully (knock, scratch and palm slap in the guided sequence).
This last result is operator-reported; no continuous prediction log or video
was saved, and there are no measured repetition counts, latency or error rates.
A single screenshot cannot establish the full output label set of a trial.

GUI output is per-window classification with the band-energy gate, without
trial-tuned smoothing/cooldown or the offline event-mean aggregation used for
the 96% take-grouped CV score. Next formal validation should preserve full
prediction sequences and test independent actions and varied adversarial
neutral behavior before freezing decision-layer parameters.
