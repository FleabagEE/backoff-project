# C test protocol: 20 evaluation trials + slide check

Status: **NOT YET RUN on hardware.** Every result cell below is blank and must be
filled during the actual session. Do not copy numbers from mock runs into it.

Sources: group rule in `SETUP.md` ("5 positive + 5 negative trials per target"),
the trial plan in `docs/scratch_v2.md`, the scoring in `trial_replay.score_trial`,
and B's `trial_passes` on `origin/model-training`.

## Definitions

- **Label set:** every finalized label that B's pipeline outputs, after the energy
  gate and smoothing, from SPACE start to SPACE stop. That includes the quiet
  onset and the tail. The labels are B's set: `{neutral, knock, rub}`. The slide
  app must receive this same finalized label, not a separate one.
- **knock:** a knuckle knock at normal force on the KNOCK pad (the farther bandage).
- **rub:** a fingernail scratch, back and forth, about 1 s, on the exposed center
  of the taped 3 x 5 cm paper pad. Fingertip rubbing no longer counts as `rub`.
- **Tester note** (read it aloud to the performer): "Knock with a knuckle on the
  knock pad at normal force. Scratch back and forth with a fingernail on the paper
  pad. Do not touch the red pickup."

## Scoring (same rule as `trial_replay.score_trial` / B `trial_passes`)

| Trial type | PASS when the label set is | FAIL examples |
|---|---|---|
| knock_pos | exactly `{knock}` or `{neutral, knock}` | `{neutral}`, `{neutral, knock, rub}` |
| rub_pos | exactly `{rub}` or `{neutral, rub}` | `{neutral}`, `{neutral, knock, rub}` |
| knock_neg | contains **no** `knock` | `{neutral, knock}` |
| rub_neg | contains **no** `rub` | `{neutral, rub}`; `{neutral, knock}` is a PASS here |

A single stray frame fails the trial. An empty set, or a label outside the three,
makes the trial **invalid**, not a pass. Invalid trials and capture faults are
re-recorded and listed in the failure log. Failed trials are never re-recorded or
dropped.

Slide-side observation is recorded **separately** and does not change the official score:

| Trial type | Expected slide behaviour (start each trial on page 2 of 3) |
|---|---|
| knock_pos | exactly one NEXT (page 2 -> 3) |
| rub_pos | exactly one PREVIOUS (page 2 -> 1) |
| knock_neg | no NEXT |
| rub_neg | no PREVIOUS (a NEXT from the knuckle-knock negative is expected) |

## Setup checklist (before trial 1)

1. A confirms the frozen setup from `docs/scratch_v2.md`: same gain mark, the
   pickup and its restraint untouched, the paper pad taped on all four edges,
   Windows input 100 with enhancements OFF.
2. B starts the live pipeline with the model they intend to submit. Write the
   model file name and its hash in the header below. Do not change the model,
   gate or smoothing during the 20 trials.
3. C starts the slide app with a log:
   `python c_app\slide_demo.py --log c_app\trial_log_YYYYMMDD.csv`
   Before each trial, press **Home** and then **Right** so the app is on page 2.
4. Smoke test (not scored): one knock, one scratch and 5 s of quiet. Confirm the
   labels reach the app ("received" counter rises, the gate returns to "ready").

## Running one trial (8 s, per scratch_v2)

| Time | Performer | Operator |
|---|---|---|
| 0-2 s | stay still | press SPACE (start), say "still" |
| 2-3 s | perform the action **once** (knock, or about 1 s of scratch) | say "now" |
| 3-8 s | stay still | at 8 s press SPACE (stop) and read the printed label set |

Write down the label set exactly as printed, then the slide page before and after.
Order: interleave the types (e.g. K+, R+, K-, R-, repeat ×5) and keep that order
even if a trial fails.

## Session header

| Field | Value |
|---|---|
| Date / time |  |
| Location / table |  |
| Performer(s) |  |
| Operator / scorer |  |
| B model file + sha256 |  |
| Gate / smoothing config (file or commit) |  |
| Git commit of this repo |  |
| Slide app log file |  |

## Score sheet

`action_performed` values come from the `docs/scratch_v2.md` trial plan.

| # | trial_type | action_performed | Label set (as printed) | PASS / FAIL / INVALID | Page before -> after | Notes |
|---:|---|---|---|---|---|---|
| 1 | knock_pos | normal knock, dominant hand, pad center |  |  |  |  |
| 2 | rub_pos | scratch_nail_paper normal, right index |  |  |  |  |
| 3 | knock_neg | one paper scratch |  |  |  |  |
| 4 | rub_neg | one knuckle knock |  |  |  |  |
| 5 | knock_pos | light knock, dominant hand |  |  |  |  |
| 6 | rub_pos | scratch_nail_paper light, right index |  |  |  |  |
| 7 | knock_neg | one palm slap |  |  |  |  |
| 8 | rub_neg | one palm slap |  |  |  |  |
| 9 | knock_pos | firm knock, dominant hand |  |  |  |  |
| 10 | rub_pos | scratch_nail_paper normal, left index |  |  |  |  |
| 11 | knock_neg | one fingertip tap |  |  |  |  |
| 12 | rub_neg | one finger flick |  |  |  |  |
| 13 | knock_pos | normal knock, other hand |  |  |  |  |
| 14 | rub_pos | scratch_nail_paper normal, right middle |  |  |  |  |
| 15 | knock_neg | place phone once |  |  |  |  |
| 16 | rub_neg | drag object briefly |  |  |  |  |
| 17 | knock_pos | normal knock, pad edge |  |  |  |  |
| 18 | rub_pos | scratch_nail_paper normal, across pad |  |  |  |  |
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
- **stray**: an extra frame of another label.
- **cross**: knock and rub confused.
- **double**: the slide turned more than once.
- **late**: the label arrived after stop.
- **operator**: performer or timing error.
- **capture**: dropout or device problem.
- **network**: the label did not reach the slide app.

| # | Time | Expected | Label set | Slide (before -> after) | Suspected cause | Evidence (log rows / B output) | Action taken |
|---:|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |

Rules for the log:
- Copy the slide app CSV rows that cover the trial window. Use `monotonic_s` and the `decision` column.
- Keep failed trials in the score. A re-record is allowed only for INVALID or capture faults, and both attempts stay listed.
- If the label set passes but the slide is wrong, or the reverse, flag it. It means the slide app and the trial recorder are not reading the same label stream.

## Software-only rehearsal (not a result)

Without the sensor, the scorer can practise the sheet with
`python c_app\mock_sender.py --interactive`. These runs check the app, not the
classifier. Do not put them in the score sheet.
