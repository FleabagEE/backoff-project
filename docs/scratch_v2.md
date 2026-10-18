# Interaction 2 v2: rub label now means nail scratch on paper

Current decision, October 18, 2026: preserve the interface label `rub`, but its
meaning is now fingernail scratching back and forth on a printer-paper pad.
Old fingertip rubbing on the bandage/pickup is superseded. All old rub feature
takes are excluded from current fitting AND current holdout by qa_dataset.py;
the original NPZ, logs, calibration and old QA exports are retained as history.
Explicit historical inventory: interaction2_superseded_sources.csv. Old pilot
sessions remain excluded. Old train.npz/holdout.npz archives are NOT current v2 data.

## Reason for the change: signal feasibility, not accuracy

Run set measurements/nail_scratch_feasibility contains five complete 10 s runs,
200 nonoverlapping 50 ms windows each, ch2 at the same gain/configuration.
Quiet median=0.11854%FS, quiet P95=0.12359%FS.

| Method | Median contrast to quiet median | P10 contrast | Windows above quiet P95 |
|---|---:|---:|---:|
| old normal fingertip rub | +9.42 dB | -0.18 dB | 73.0% |
| LIGHT nail scratch on paper | +11.13 dB | +4.79 dB | 98.5% |
| NORMAL nail scratch on paper | +9.97 dB | +5.90 dB | 100.0% |

Hardest-knock test peak=44.296%FS; zero digital clipping/overflow; hardware CLIP
did not flash. FEASIBLE under the agreed energy criteria. Median improvement is
only 1.71 dB for light scratch vs old; the main benefit is P10/coverage consistency.
This does not establish classifier separability, stranger performance or SET success.

## Frozen physical setup

Same gain A mark, pickup mounting, bandage restraint and cable arrangement;
Windows input100, enhancements OFF, +48V OFF; WASAPI USB Audio CODEC physical
ch2 stereo int16 48000Hz/capture480/FFT2400 samples50ms/original1200 features.
Board17x27cm directly on table. KNOCK remains on the farther bandage.
One printer-paper sheet taped flat on all FOUR edges in the near-pickup zone;
scratch only its exposed paper center. Do not touch pickup, its restraint or cable.
Paper directly on board, not layered over the old soft bandage. Keep the former
bandage available/untouched as during the comparison; don't move the sensor.
Actual paper size: **3 x 5 cm**, confirmed by A. Exact paper stock and center
coordinates from the board's left/top edges remain pending confirmation.
Photograph full board, paper/edge tape and gain mark under docs/setup/; bring
spare sheets of the SAME stock, cut size, edge tape and marked placement.
Replace worn/loose paper consistently and recheck quiet/light scratch/hard knock.
Direct table contact remains a cross-table vibration risk.

## Recorded train and remaining capture

Source scratch train session: data_sessions/final_v2/20261018_101351_e6b598a9.
A recorded eleven scratch-labelled train takes, eight medium/firm and three light.
final_v2_exclusions.csv excludes ONLY the later duplicate left-light take from
derived data; retain its raw file. Ten accepted training takes, two light.
This first source used the old GUI config's bandage setup_id; its notes and this
protocol establish the actual paper surface. Do NOT rewrite its raw config.

Two scratch holdout takes remain: a fresh medium right-index along-pad take and
a fresh medium/firm left-middle across-pad take, each25s. Use updated GUI with
DATA SPLIT=holdout, class rub, notes scratch_nail_paper holdout ... . Each Record
opens a modal naming the class and notes and explicitly stating WILL SAVE AS
HOLDOUT. Confirm EACH take to start. Training eligibility is false. Restarting
creates a new source folder; old train takes remain safe, and QA merges folders.

## Evaluation trials for B: 20 x 8 s, never training data

Run `uv run visualizer.py --final --session-root data_sessions/final_v2_trials`.
Mode Train is the capture workspace, but select Recording kind=trial. The banner
must say EVALUATION TRIAL ONLY - NEVER TRAIN. Trial capture ignores the take
duration field: fixed8s, split=trial, recording_kind=trial. Enter action_performed.
The GUI phase text is STAY STILL 0-2s, ACTION ONCE NOW 2-3s, STAY STILL 3-8s.
One knock OR one ~1s scratch, then stop moving. A one-second scratch includes
back-and-forth motion; do not scratch continuously for the full8s.

| trial_type | Five action_performed values (one take per value) |
|---|---|
| knock_pos | normal dominant center; light dominant; firm dominant; normal other hand; normal patch edge |
| rub_pos | scratch_nail_paper normal right index; light right index; normal left index; normal right middle; normal across pad |
| knock_neg | one paper scratch; one palm slap; one fingertip tap; place phone once; type briefly nearby |
| rub_neg | one knuckle knock; one palm slap; one finger flick; drag object briefly; rest hand once |

Use actual descriptive action_performed text. No gain/mounting changes. Each
trial is autosaved individually; early stop or capture faults mark it excluded.
No evaluation rows enter CollectionSession's default aggregate training export.
Never interpret positive trial labels as per-window training labels: quiet onset
and tail belong to the evaluated trial SET too.

## Combined QA after real holdout and trial recordings exist

Base=20261017_195725_85cb47b5 knock+neutral, with final_split_corrections.csv;
add all accepted new scratch-only source folders through repeated --scratch-session.
Use --exclusions docs/final_v2_exclusions.csv. Capture/feature settings must match.
Old rub is removed, old knock/neutral is retained. Neutral 'drag object' takes
are flagged friction_review for B; do not relabel/exclude them automatically.
Original knock/neutral held-out data was evaluated once before; this is reused
development evidence, not an untouched final test.

QA baseline remains log1p/StandardScaler/LinearSVC and GroupKFold by take.
Holdout excluded from fitting; don't randomly split windows. New QA is pending,
so no claim of improvement over old51.5%/70.2% yet.

Replay demonstration after merged exports exist:

```cmd
uv run trial_replay.py data_sessions/final_v2_trials/ACTUAL_SESSION --baseline-train handoff/ACTUAL_V2_REVIEW/train.npz --output handoff/ACTUAL_V2_REVIEW/trial_demo.json
```

B's real interface: --adapter module:factory --model PATH --policy module:function.
factory(model_path) returns predictor(X)->class-name strings; it owns matching
model preprocessing. Policy(label,rms_fs,peak_fs,elapsed_s,state)->one final label
per frame, with fresh state for every trial. No gate defaults to identity. All
windows, including quiet onset/tail, contribute to the SET. Positive passes only
{target} or {neutral,target}; negative passes only if target absent. Empty sets
are rejected as invalid evaluation. Report counts and whether all20 trials exist.

## Tester note for C

"Knock with a knuckle on the knock pad at normal force. Scratch back and forth
with a fingernail on the paper pad. Do not touch the red pickup."

## Delivery

Current v2 ZIP and cloud link: PENDING actual two holdout + twenty trial takes,
combined QA and replay. Never commit .npz/.zip; code/docs/logs/QA only go to Git.
The previous A_final_20261017_195725_85cb47b5.zip is an OLD interaction archive;
keep it, but don't give its old rub training data to the new model.

Verification: 19 collection/QA/recording-policy tests passed after the changes,
including mocked GUI modal confirmation on every holdout request and replay of
synthetic evaluation-only data. Actual updated GUI holdout/trial capture remains
to be confirmed by A. Synthetic test results are not real bakeoff trial results.
