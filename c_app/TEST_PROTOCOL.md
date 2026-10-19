# C test protocol: 20 evaluation trials + slide check (wood v3)

Status: **NOT YET RUN on hardware.** Every result cell below is blank and must be
filled in during the actual session. Do not copy numbers from mock runs, CV
reports or operator impressions into it.

Sources:
- the group rule in `SETUP.md` ("5 positive + 5 negative trials per target");
- the scoring in `trial_replay.score_trial`, which is the same as B's
  `trial_passes` on `origin/model-training`;
- the wood v3 setup in `docs/HANDOFF_C.md` and `MODEL_NOTES.md`.

The action list below adapts the earlier `docs/scratch_v2.md` table to bare
wood, and the 8 s timing comes from that document too. **A and B still have to
confirm both for v3.**

## Definitions

- **Setup:** `A_wood30x30x6_v3_candidate2`, a 30 x 30 cm board, 6 mm thick, bare
  wood, directly on the table. The model is the pair
  `a_models/wood_v3_20261019_135608_v1/model.joblib` and `decision_params.json`.
  Never mix in another model or parameter file.
- **knock:** one knuckle knock on the board.
- **rub:** the fingernail edge scratched back and forth on the **bare wood**,
  about 1 s. Paper pads and fingertip rubbing are no longer part of this definition.
- **Label set:** every final label shown as `Prediction:` by `visualizer.py`
  between trial start and stop. That includes the quiet start and the tail. The
  label set is drawn from `{neutral, knock, rub}`.
- **Tester note** (read it aloud): "Knock once with a knuckle on the board. To
  scratch, move a fingernail edge back and forth on the bare wood. Do not touch the
  pickup, its tape or the cable."

### Where the label set comes from

The GUI has **no live SPACE trial recorder yet**. Until B provides one, use the
slide app log as the record of the GUI's final label stream. `visualizer.py`
sends the first label and then every change, and the slide app writes each one
to its CSV.

For a trial running from `start` to `stop` (wall-clock times written down by the operator):

> label set = { the last label received **before** `start` } ∪ { every label received between `start` and `stop` }

If B's recorder becomes available, use its printed set and note which one you
used in the session header. Both read the same final label, so they must agree.
If they disagree, log it as a failure of type `network`.

## Scoring (same rule as `trial_replay.score_trial` / B `trial_passes`)

| Trial type | PASS when the label set is | FAIL examples |
|---|---|---|
| knock_pos | exactly `{knock}` or `{neutral, knock}` | `{neutral}`, `{neutral, knock, rub}` |
| rub_pos | exactly `{rub}` or `{neutral, rub}` | `{neutral}`, `{neutral, knock, rub}` |
| knock_neg | contains **no** `knock` | `{neutral, knock}` |
| rub_neg | contains **no** `rub` | `{neutral, rub}`; `{neutral, knock}` is a PASS here |

A single stray label fails the trial. An empty set, or a label outside the three,
makes the trial **invalid**, not a pass. Invalid trials and capture faults are
re-recorded and listed in the failure log. Failed trials are never re-recorded or
dropped.

Slide-side observation is recorded **separately** and does not change the
official score. The slide app's one-turn rule and cooldown are not part of
recognition. Start each trial on page 2 of 3: press Home, then Right.

| Trial type | Expected slide behaviour |
|---|---|
| knock_pos | exactly one NEXT (page 2 -> 3) |
| rub_pos | exactly one PREVIOUS (page 2 -> 1) |
| knock_neg | no NEXT |
| rub_neg | no PREVIOUS (a NEXT from the knuckle-knock negative is expected) |

## Setup checklist (before trial 1)

1. A confirms the v3 setup: the same gain mark, Windows input level 100,
   enhancements OFF, phantom power OFF, and the pickup tape untouched.
2. Window 1 (slide app with log):
   `uv run python c_app\slide_demo.py --log c_app\trial_log_YYYYMMDD.csv`
3. Window 2 (live inference, sends to `127.0.0.1:5005` by default):
   `uv run visualizer.py --setup-id A_wood30x30x6_v3_candidate2 --scratch-surface wood --trained-model a_models/wood_v3_20261019_135608_v1/model.joblib --decision-params a_models/wood_v3_20261019_135608_v1/decision_params.json`
4. Do not change the model, gate or slide `--cooldown` during the 20 trials.
5. Smoke test (not scored): one knock, one scratch, then 5 s of quiet. Confirm the
   slide window's `received` counter rises and the gate returns to `ready`.

## Running one trial (8 s; timing to be confirmed for v3)

| Time | Performer | Operator |
|---|---|---|
| 0-2 s | stay still | note the start time, say "still" |
| 2-3 s | perform the action **once** (one knock, or about 1 s of scratching) | say "now" |
| 3-8 s | stay still | note the stop time at 8 s |

Write down the label set, then the slide page before and after the trial.
Interleave the types (K+, R+, K-, R-, then repeat 5 times) and keep that order
even when a trial fails.

## Session header

| Field | Value |
|---|---|
| Date / time |  |
| Location / table |  |
| Performer(s) |  |
| Operator / scorer |  |
| Model folder + `model_sha256` from decision_params.json |  |
| Git commit of this repo |  |
| Label set source (slide log CSV / B recorder) |  |
| Slide app log file |  |

## Score sheet

These `action_performed` values are the proposal for v3 and need A/B confirmation.

| # | trial_type | action_performed | Label set | PASS / FAIL / INVALID | Page before -> after | Notes |
|---:|---|---|---|---|---|---|
| 1 | knock_pos | normal knuckle knock, dominant hand, board center |  |  |  |  |
| 2 | rub_pos | nail-edge scratch on wood, normal, right index |  |  |  |  |
| 3 | knock_neg | one nail-edge scratch on wood |  |  |  |  |
| 4 | rub_neg | one knuckle knock |  |  |  |  |
| 5 | knock_pos | light knuckle knock, dominant hand |  |  |  |  |
| 6 | rub_pos | nail-edge scratch on wood, light, right index |  |  |  |  |
| 7 | knock_neg | one palm slap |  |  |  |  |
| 8 | rub_neg | one palm slap |  |  |  |  |
| 9 | knock_pos | firm knuckle knock, dominant hand |  |  |  |  |
| 10 | rub_pos | nail-edge scratch on wood, normal, left index |  |  |  |  |
| 11 | knock_neg | one fingertip tap |  |  |  |  |
| 12 | rub_neg | one finger flick |  |  |  |  |
| 13 | knock_pos | normal knuckle knock, other hand |  |  |  |  |
| 14 | rub_pos | nail-edge scratch on wood, normal, right middle |  |  |  |  |
| 15 | knock_neg | place phone once |  |  |  |  |
| 16 | rub_neg | drag object briefly |  |  |  |  |
| 17 | knock_pos | normal knuckle knock, off-center position |  |  |  |  |
| 18 | rub_pos | nail-edge scratch on wood, other direction |  |  |  |  |
| 19 | knock_neg | type briefly nearby |  |  |  |  |
| 20 | rub_neg | rest hand once |  |  |  |  |

## Summary

| Trial type | Passed / 5 | Invalid (re-recorded) | Slide behaviour as expected / 5 |
|---|---:|---:|---:|
| knock_pos |  |  |  |
| rub_pos |  |  |  |
| knock_neg |  |  |  |
| rub_neg |  |  |  |
| **Total** | **/ 20** |  |  |

All 20 trials recorded (5 per type)? ☐ yes ☐ no

## Failure log

Fill in one row for every FAIL, INVALID, or case where the slide behaviour
differs from the score. For the cause, choose one or more:
- **miss**: the target never appears.
- **stray**: an extra label of another class.
- **cross**: knock and rub confused.
- **double**: the slide turned more than once.
- **late**: the label changed after stop.
- **operator**: performer or timing error.
- **capture**: dropout, `WAIT / NO FRESH AUDIO`, or a device problem.
- **network**: the label did not reach the slide app, or the sources disagree.

| # | Time | Expected | Label set | Slide (before -> after) | Suspected cause | Evidence (log rows) | Action taken |
|---:|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |

Rules for the log:
- Copy the slide app CSV rows that cover the trial. Use `wall_time`, `label`, `decision` and `page`.
- Keep failed trials in the score. A re-record is allowed only for INVALID or capture faults, and both attempts stay listed.
- The slide cooldown can hide a second wrong label from the slide display, but
  the trial is still scored on the full label set.

## Software-only rehearsal (not a result)

Without the sensor, the scorer can practise the sheet with
`python c_app\mock_sender.py --interactive`. These runs check the app, not the
classifier. Do not put them in the score sheet.
