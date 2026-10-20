# C test protocol: 20 evaluation trials + slide check (wood v3)

Status: **NOT YET RUN on hardware.** Every result cell below is blank and must be
filled during the actual session. Do not copy numbers from mock runs, CV
reports or operator impressions into it.

**Formal scoring uses the model-side SPACE trial recorder** (B, in
`visualizer.py` Infer mode: SPACE starts and stops a trial, the set is scored
and logged to `trial_logs/`). The slide app CSV is for troubleshooting only and
is never the official score.

Sources:
- the group rule in `SETUP.md` ("5 positive + 5 negative trials per target");
- the scoring in `trial_replay.score_trial`, which is the same as B's
  `trial_passes`;
- the wood v3 setup in `docs/HANDOFF_C.md` and `MODEL_NOTES.md`.

The action list adapts the earlier `docs/scratch_v2.md` table to bare wood.
**A and B still have to confirm it for v3**, along with the trial length.

## Definitions

- **Setup:** `A_wood30x30x6_v3_candidate2`, a 30 x 30 cm board, 6 mm thick, bare
  wood, directly on the table. The model is the pair
  `a_models/wood_v3_20261019_135608_v1/model.joblib` and `decision_params.json`.
  Never mix in another model or parameter file.
- **knock:** one knuckle knock on the board.
- **rub:** the fingernail edge scratched back and forth on the **bare wood**,
  about 1 s.
- **Label set:** every final label the model side outputs between SPACE start
  and SPACE stop, including the quiet start and the tail. It comes from B's
  SPACE recorder and is drawn from `{neutral, knock, rub}`. The recorder must use
  the same final label stream that `visualizer.py` shows as `Prediction:` and
  sends to the slide app.

## Rules for the performer and operator

1. **Practice first, once per action type, before any formal trial.** The
   performer does one knock, one scratch, and one example of each negative action
   on the list. Practice is not scored or recorded as a trial. Give instructions
   only during practice.
2. Before formal trials, tell the performer the procedure once: wait until the
   operator starts the trial, stay still, do the action **once**, stay still until
   the operator stops the trial. For a negative trial, do the named action once.
3. **During formal trials: no prompts, cues, countdowns, corrections or physical
   help.** Do not call out "still" or "now" and do not point. The operator only
   starts and stops the recorder, and says which trial number and action comes next.
4. Keep every formal trial, pass or fail. A re-record is allowed only for an
   INVALID trial (an empty set or a recorder/capture fault, as defined below), and
   both attempts stay in the log.
5. Do not change the model, gate, setup or slide app settings during the 20 trials.

## Scoring (same rule as `trial_replay.score_trial` / B `trial_passes`)

| Trial type | PASS when the label set is | FAIL examples |
|---|---|---|
| knock_pos | exactly `{knock}` or `{neutral, knock}` | `{neutral}`, `{neutral, knock, rub}` |
| rub_pos | exactly `{rub}` or `{neutral, rub}` | `{neutral}`, `{neutral, knock, rub}` |
| knock_neg | contains **no** `knock` | `{neutral, knock}` |
| rub_neg | contains **no** `rub` | `{neutral, rub}`; `{neutral, knock}` is a PASS here |

A single stray label fails the trial. An empty set, or a label outside the three,
makes the trial **INVALID**, not a pass.

The slide app is **not** part of scoring. It turns one page per final action
message it receives and makes no decision of its own. Slide behaviour is recorded
in a separate column and never changes PASS/FAIL. Start each trial on page 2 of 3
(press Home, then Right). The slide column is meaningful only with the GUI's
default event decision (`--decision event`); in per-window mode (`--decision
window` or Load Model) pages follow every label change.

| Trial type | Expected slide behaviour |
|---|---|
| knock_pos | exactly one NEXT (page 2 -> 3) |
| rub_pos | exactly one PREVIOUS (page 2 -> 1) |
| knock_neg | no NEXT |
| rub_neg | no PREVIOUS (a NEXT from the knuckle-knock negative is expected) |

## Setup checklist (before practice)

1. A confirms the v3 setup: the same gain mark, Windows input level 100,
   enhancements OFF, phantom power OFF, and the pickup tape untouched.
2. Window 1 (slide app; the log is for troubleshooting only):
   `uv run python c_app\slide_demo.py --log c_app\trial_log_YYYYMMDD.csv`
3. Window 2 (live inference, sends to `127.0.0.1:5005` by default):
   `uv run visualizer.py --setup-id A_wood30x30x6_v3_candidate2 --scratch-surface wood --trained-model a_models/wood_v3_20261019_135608_v1/model.joblib --decision-params a_models/wood_v3_20261019_135608_v1/decision_params.json`
4. Confirm the GUI shows the BAKEOFF TRIAL panel and `raw window: ... | event: idle`
   under the prediction (event decision active). If the event line is missing,
   the GUI is in per-window mode: stop here, do not run formal trials or the slide
   check.
5. Smoke test, not scored: in the slide window, `received` rises, `heartbeats`
   keeps counting while the GUI is in Infer, and `page turns` stays unchanged
   while quiet.

## Session header

| Field | Value |
|---|---|
| Date / time |  |
| Location / table |  |
| Performer(s) |  |
| Operator / scorer |  |
| Model folder + `model_sha256` from decision_params.json |  |
| Git commit of this repo |  |
| SPACE recorder (who / version) |  |
| Slide app log file (troubleshooting) |  |
| Practice done for every action type? ☐ yes |  |

## Score sheet

These `action_performed` values are the proposal for v3 and need A/B confirmation.

| # | trial_type | action_performed | Label set (SPACE recorder) | PASS / FAIL / INVALID | Slide page before -> after | Notes |
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
- **performer**: the action was not as listed.
- **capture**: dropout, `WAIT / NO FRESH AUDIO`, or a device problem.
- **network**: the label did not reach the slide app.

| # | Time | Expected | Label set (SPACE) | Slide (before -> after) | Suspected cause | Evidence | Action taken |
|---:|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |

The slide app CSV may be quoted as evidence, for example the `wall_time`,
`label` and `decision` rows around the trial. It helps explain a failure but it
never replaces or overrides the SPACE recorder's label set.

## Internal debugging only (never formal results)

These steps are for checking the pipeline before formal trials, or while the
SPACE recorder does not exist. Mark any sheet produced this way
**"INTERNAL DEBUG – not a formal trial"**.

- A guided 8 s run, with the operator calling "still" for 0–2 s, "now" at
  2–3 s, and "still" again until 8 s.
- An approximate label set worked out from the slide app CSV: the last label
  received before start, plus every label received between start and stop.
- `python c_app\mock_sender.py --interactive` to practise using the sheet
  without the sensor. This checks the app, not the classifier.
