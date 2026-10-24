CURRENT RUNNABLE SNAPSHOT (October 24): [v1 + gate1.2x + B event decisions + C slides](WORKING_GATE120_20261024.md). User reports it runs; formal fresh acceptance pending. v2 below is an alternative model, not selected by the working launch command.

LATEST MODEL UPDATE (October 20): v2 includes 20 interference neutral takes (95 total). See [neutral20 results](WOOD_V3_NEUTRAL20_20261020.md). Mean-score CV91/95; B event trial-set87/95, with knock misses and one duplicate. Gate/capture/decoder unchanged; fresh live test pending. Explicitly load the v2 model AND params pair. The v1 snapshot below is historical.

# Current A/B/C integration snapshot — October 20, 2026

Branch: **a-b-event-integration-20261020**.

This branch merges A `b111a0c` (working trial buttons/keyboard fallback, reports
and v1 model pair) with B `db4f9d4` (event-level live decoder and SPACE trials).
C latest `f577b85` is merged: its slide receiver executes one page turn per non-heartbeat action message, with no frontend cooldown or neutral confirmation. Heartbeats never turn pages. A's
separate unfinished event-T implementation remains parked locally and is NOT
part of this snapshot. No teammate source branch is modified.

## What is running

- Same wood-v3 v1 model: `a_models/wood_v3_20261019_135608_v1/model.joblib`.
- Same paired `decision_params.json`, same band-energy gate and capture/features.
- B event mode (default; explicit `--decision event`): trigger/vote energy is
  the existing gate, max collection1s, end after .3s without voting frames,
  minimum2 votes, majority class with mean-score tie-break, label hold.25s,
  quiet rearm.15s. Neutral can win. These defaults live in B's decoder code and
  are also recorded in each trial log; the original v1 JSON has not been edited.
- Final labels are shared by Prediction, the SPACE/button trial recorder and
  C's UDP receiver. The grey raw-window label may differ during collection.
- Clickable START/STOP TRIAL plus SPACE handlers and polling fallback are
  included directly. No machine-specific local adapter is needed on this branch.

## Start

Fetch and switch in your own clone (save local work first):

```cmd
git fetch origin
git switch a-b-event-integration-20261020
uv sync
```

Close all other sensor GUIs. To use slides, start the receiver FIRST:

```cmd
uv run python c_app\slide_demo.py --log "%TEMP%\backoff-event-slide-log.csv"
```

Then start the ONLY sensor capture in a second terminal in the same checkout:

```cmd
uv run visualizer.py --setup-id A_wood30x30x6_v3_candidate2 --scratch-surface wood --trained-model a_models/wood_v3_20261019_135608_v1/model.joblib --decision-params a_models/wood_v3_20261019_135608_v1/decision_params.json --decision event --slide-udp 127.0.0.1:5005
```

For classification-only tests, use `--slide-udp off`. For the old per-window
baseline, explicitly use `--decision window`. Do not accidentally launch an old
worktree: the a-tuning branch itself still retains its v1 window runtime.

Select the intended trial type before starting. Click START, perform ONE action,
wait for the prediction tail to return to neutral, click STOP, inspect Set and
Result. Practice/undo/reset/log features remain available. SPACE is local to the
inference window; its physical keyboard operation is not confirmed on A's
laptop, while click-button operation is confirmed. Logs stay in trial_logs/ and
are never training data. Slide behavior runs continuously even outside a trial.

## Evidence and limits

- Combined automated validation: **88 repository +25 C slide tests =113 passed**.
- Earlier B-only validation:82 tests; replay of the original ten development
  actions through B's decoder gave knock5/5 and rub5/5. These are reused
  development actions, not a fresh success-rate measurement.
- A's subsequent real button trials include rub successes after A reported
  longer scratches, but also neutral-only misses and a knock-only error.
  Do NOT claim stable short-scratch recognition or completed acceptance.
- The first B trial was configured knock_pos while A was guided to scratch:
  its set was neutral/rub. Preserve that raw record; do not count it as a true
  knock-recognition failure or silently relabel it.
- See [the snapshot trial summaries](b_event_trial_snapshot_20261020.json) for
  the actual saved outcomes, including failures. Trial duration is the WHOLE
  start/stop interval; it does not measure scratch duration.
- Slide testing has only just started. Receiver logs may contain page changes,
  but action-to-slide correspondence was not confirmed by A at snapshot time.
  Do not mark the proposed single-knock/return-scratch test complete yet.
- Full independent knock/rub series, quiet30s and adversarial neutral checks are
  pending. Neutral training still contains only stillness. No new data/model
  fitting, gate changes or hardware changes were performed for this snapshot.

## Data/version preservation

Models are small and included in Git. NPZ, trial_logs/ and transfer ZIP archives
remain local. The public JSON is a derived result summary, not raw feature data
or the full per-frame trial log. Original recordings and parked WIP are retained.

Model SHA256:
`605e7a3c0dd04029783c6f5997d1872e94483786dd9bd9a74249f6bff90cc6ac`.
Params SHA256:
`bcc3c40a475ab473371fd433f7e5c4a495e5ec035cbdd466370ca92ee0dedba2`.
