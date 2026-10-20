# Teammate A progress report — October 17, 2026 (America/Los_Angeles)

## CURRENT: 75 wooden-board takes trained (October 19)

LATEST STEERING (October20): integrate b-space-trial-mode FIRST, then return to
event decisions. Source88b9905 and its C slide/UDP dependencies are merged into
a-tuning. See docs/SPACE_TRIAL_MODE.md for launch and SPACE scoring workflow.
68 repository +24 C tests pass (92 total). Model/gate/capture/features unchanged.
Unfinished event_decision.py, select_event_time.py and event-v2 params/report
are saved in the named WIP stash, excluded from this integration and runtime.
No new physical tests were performed. The rub-onset ordering issue still exists.

CONTROLLED LIVE DIAGNOSIS UPDATE: see docs/live_test_20261019.md. Five knocks
give5 next turns. Five scratches give5 wrong next attempts (1 moved,4 blocked)
and1 previous turn: transient K precedes sustained R and C rejects R until
neutral re-arm. This supersedes earlier informal "all successful" observations.
Live/offline parity:0 raw/gate label mismatches in1538 windows; actual UDP
561/561 payloads matched; capture status0. No retraining or live decision changes.
Actual current model K=1 both classes/cooldown0, C frontend .8s/.6s neutral hold.
Event-mean replay5/5 K and5/5 R;250ms pending-K alternative5/5 K and4/5 R;
K2/R6 only1/5 R; cooldown-only changes0/5 R. Replay scores are development,
not independent validation. Recommend prospective event-level live test next.
Diagnostic code stays on live-diagnosis-20261019, original C branch unchanged.
Thirty-second quiet/adversarial series and prospective fix validation pending.

Latest delivery: origin/a-tuning contains code, docs, compact model.joblib and
paired decision_params.json. C's entry point is docs/HANDOFF_C.md. See
docs/WOOD_V3_REALTIME_CHECK.md for preliminary live observations and one saved
palm-slap neutral replay (42/42 windows neutral). A reports basic live checks
successful; no logged trial series/latency measurement exists. The saved palm
take's raw split is accidentally train, but its isolated evaluation session is
excluded from all fitting; raw files/metadata remain untouched. No fingertip
test capture has been confirmed. Model and parameters remain unchanged.

This entry supersedes the historical collection plans and pending statements
below. A collected 25 two-second takes per class in
`data_sessions/final_v3/20261019_135608_9c907587` and explicitly confirmed ALL
25 neutral takes are quiet. Only this source session was used; earlier data
remain untouched and excluded. Setup is A_wood30x30x6_v3_candidate2.

Model and paired parameters: `a_models/wood_v3_20261019_135608_v1/`.
See `MODEL_NOTES.md` for the commands, cleaning, CV table and limitations.
Five-fold take-grouped model-selection CV selects <=8kHz/C=.0003:
72/75 take predictions correct (96%); N 25/25, K 22/25, R 25/25.
Two K takes have no detected event; a third weak/early event predicts neutral.
No independent adversarial, holdout, development or fresh test evaluation.
No final acceptance/durability PASS is implied. The gate uses new quiet P95
band energy; smoothing/cooldown are provisional, not trial-tuned.
GUI startup can load the two artifacts and uses window gating; event-mean
take classification is available offline and is the source of the 96% score.
All 41 tests pass. Audio capture, FFT and feature processing are unchanged.

## Historical v3 restart: new wooden board, acceptance pending (October 19)

CURRENT RECORDING REQUEST supersedes all25s plans below: a CLEAN final_v3
session,2-second TRAIN/HOLDOUT takes, exactly ONE action per take (scratch ~1s),
or one neutral action/stillness. New --fast-takes launch defaults to take/train/
2s/performer A; R shortcut, silent0.3s cue, persistent notes, large per-class
counters and preflight checks. See docs/FINAL_V3_TWO_SECOND_WORKFLOW.md.
No audio/FFT/feature processing changes, no old-data modifications. final_v3 root
was absent and is now created/verified empty (0entries,0NPZ); each launch makes a unique child session,
zero recordings, no data import/resume. New take counts/quota (~130total) need
explicit batch planning; do not carry forward25s quotas or5s calibration prefix.
The prior event segmentation/checkpoint is retained as historical code, not
silently applied unchanged to2s takes. Current source metadata uses
single_action_2s / offline_single_action_segmentation_required. Formal recording
has NOT started in this session-setup turn; tests are synthetic/temp only.
All37 discovered tests pass, including7 new fast-take cases for real widgets,
R-key handling/typing protection, auto-stop/save, persistent notes, preflight
warnings, per-take holdout confirmation and excluded early stops.

AUTHORITATIVE latest steering: A canceled the separate mini pilot and explicitly
requests full final_v3 collection now, with a checkpoint after TWO interleaved
K/R/N rounds (six takes). See `docs/FINAL_V3_EVENT_PROTOCOL.md` for rhythm,
selection, gate calibration, segmentation/label policy and checkpoint scoring.
This supersedes the six-take pilot plan below; no pilot model has been fitted.
Incomplete pilot has five takes, all class/notes match; first K take/train versus
other four diagnostic is a type inconsistency only. All five excluded from new
training/evaluation via source selection, companion pilot_wood_exclusions.csv;
raws retained. Do NOT finish or reuse pilot_wood.

New positives: ONE action every2s, visual cues at1,3,...23s, expected12 events
per25s take. GUI --event-rhythm changes cue/metadata only; FFT/features unchanged.
Offline 0.5–8kHz energy segmentation with context[-.2,+1.5]s; outside-event and
quiet-like positive fit windows DROPPED. Neutral retained. Gate calibration uses
reserved first5s of NEW quiet take, excluded from checkpoint fitting/scoring.
Compare round1/round2 both directions with fixed B8kHz/C=.001, no gate vs band
gate; report confusion/accuracy/scratch->neutral and detected event counts.
Approximate cue-based evaluation includes quiet gaps as neutral and all expected
scratch intervals, so missing detections cannot disappear from scoring. Failure:
stop, diagnose, propose ONE fix, wait for A. Six takes count if continuing. Later
compare window decisions vs event-aggregated decisions on development trials.
No final_v3 captures or actual checkpoint/event counts exist yet. All previous
candidate2 level FAIL results remain factual; A now authorizes this checkpoint
path, not a fabricated level PASS or completed durability result.

Latest steering: A requests zero-recording band analysis, then a six-take
`pilot_wood` classifier feasibility test BEFORE any formal collection. Analysis
is complete; see `docs/CANDIDATE2_BAND_FEASIBILITY.md` and derived JSON/CSV in
`handoff/candidate2_band_analysis_20261019/`. No new captures/models yet.
Deweighted smoothed FFT proxy shows scratch contrast strongest <1 kHz, not
above 8 kHz. Best light coverage over quiet P95 is 87.32%, P10 margin -0.40 dB;
candidate2 still FAILS proposed 90% contrast acceptance. Gain-noise dependence
cannot be inferred from a single-gain spectrum. Knock headroom to 70% is
13.46 dB; gain remains unchanged. Latest explicit authorization permits this
isolated pilot despite failed level acceptance; it does NOT authorize formal
collection or a hidden relaxation of spectral thresholds. Pilot data must be
excluded from final training/evaluation. Predeclared pipeline, fold plan,
independent quiet gate calibration and <=5% scratch->neutral definition are in
the report. After real pilot results, decide whether to proceed or compare a
fully adhered paper surface; no further hardware change has occurred.

Candidate2: A confirms thin double-sided tape under the pickup plus retaining
tape over the top. The ONE permitted initial acceptance re-test is now complete
and **FAILS the original criteria**. No further automatic hardware changes or
re-test loops. No formal data collection, training, or durability test started.
Session `data_sessions/diagnostics/final_v3_acceptance/20261019_125214_3db18f7f`,
setup `A_wood30x30x6_v3_candidate2`; all four valid diagnostic takes retained.

| Condition | Median RMS %FS | P10 RMS %FS | Peak %FS |
|---|---:|---:|---:|
| Quiet | 0.12974 | 0.12059 | 0.58289 |
| Normal nail scratch | 0.22467 | 0.15766 | 4.15039 |
| Light nail scratch | 0.22651 | 0.13705 | 2.02332 |
| Three hardest knocks | 0.13244 | 0.12303 | 14.86206 |

Quiet P95=0.146804% FS. Normal median improved 4.52 dB over candidate1, but
remains below ~0.3% FS. Light P10 is 0.60 dB BELOW quiet P95; 84.98% of light
windows exceed it, so the requested low-window margin is not met. Knock peak
is below 70%; no full-scale peak was captured, but raw PCM clipping counts are
not stored in GUI takes. Candidate2 hardware CLIP-lamp observation not supplied.
Do not carry forward candidate1's lamp observation as candidate2 evidence.
Normal and light medians are nearly identical in these manual runs; do not infer
a reliable force-to-level relationship. Material, mounting and operator effects
have not been isolated. Original targets remain unchanged: no PASS claim and no
formal collection without an explicit revised plan from A.

Candidate1 GUI acceptance has now FAILED (diagnostics only; no formal data).
Session `data_sessions/diagnostics/final_v3_acceptance/20261019_124115_b213e5cc`.
Use the latest 10s quiet `take_b16315a9adba44d2a2de9d28773a4ad1` as reference;
the earlier 14.532s quiet is retained but not used for this comparison.

| Condition | Median RMS %FS | P10 RMS %FS | Peak %FS |
|---|---:|---:|---:|
| Quiet (10s) | 0.11477 | 0.11252 | 0.57983 |
| Normal nail scratch on wood | 0.13355 | 0.11877 | 1.15662 |
| Light nail scratch on wood | 0.12498 | 0.11655 | 0.86670 |
| Three hardest knocks (notes saved as `knock`) | 0.11496 | 0.11206 | 8.30383 |

Quiet P95=0.117888% FS. Normal median below ~0.3% target; light P10 below
quiet P95. Hardware CLIP lamp did NOT flash during hardest knocks (A confirmed).
Knock headroom passes but does not compensate for failed scratch acceptance.
All takes valid and diagnostic; no durability check or formal data collected.
New-board normal scratch did not clearly improve on old-board GUI normal
(median/P10 0.14575/0.12178% FS). Cross-board comparisons are not controlled
material tests because mounting and action also differ.

Single proposed correction for the one permitted re-test: improve pickup-to-wood
contact with thin double-sided adhesive beneath the sensing/contact face plus
top restraint, retaining board, bare-wood scratch zone, gain and processing.
This is a coupling hypothesis supported by the previous pressure response,
not proof of a defective pickup or of the current mechanical cause. Correction
has NOT yet been performed/confirmed. If A performs it, document actual adhesive
and use new candidate setup ID `A_wood30x30x6_v3_candidate2`; repeat GUI acceptance
once, then durability only if initial levels pass. Do not mix candidate1/2 data.

A switched to a 30x30 cm, 6 mm board (wood construction unknown), ordinary tape
at pickup bottom AND top with reported full contact, no separate cable restraint,
directly on table/no padding. No paper pad. A confirmed fingernail EDGE scratching
bare wood, not skin rubbing; label stays rub. Both zones approximately 5 cm from
pickup. Exact pickup coordinates remain hand-span descriptions pending cm/photos.
See SETUP.md, candidate `A_wood30x30x6_v3_candidate1`. ALL previous sessions are
different setups, excluded from v3 training AND evaluation, originals retained.

First GUI diagnostic quiet 10s, normal wood scratch 10s, light scratch 10s,
three hardest knocks, then the 10-minute/lift/set-down/20-knock durability check
and repeat quiet/normal. Acceptance PENDING real captures; no formal data before
PASS. Same gain/audio/FFT/features. A requests model/parameters delivered to B
about 5 pm today; do not claim deadline or acceptance achieved. Work on a-tuning,
preserve model-training. After PASS: one final_v3 session, interleaved 10 knock/
10 rub/16 neutral training, six confirmed holdouts, twenty development trials,
grouped training-only model selection and trial tuning, then eight untouched
test trials and one holdout evaluation. Follow A's latest detailed request.

## Previous: October 19 integrity check — stopped after five runs

Run set `measurements/integrity_check_20261019/` is diagnostic only, never for
training. Five 10-second runs completed; each has 200 non-overlapping 50 ms ch2
windows at 48 kHz via device_check/WASAPI USB Audio CODEC. No code, gate, gain,
mounting or paper changes were made. No training, holdout or trial collection.
A asked to stop before run 6 (normal unpressed scratch), so reproducibility of
that condition was NOT measured in this run set. All originals remain local.

Fixed diagnostic thresholds: spike RMS >5x this quiet median = 0.620398% FS;
dropout RMS <half this quiet P10 = 0.060483% FS. These are window flags, not
model-gate changes or proof of an electrical fault. All five runs complete,
zero digital clipping and zero overflow. Hardware CLIP-lamp status not reported.

| Condition | Median RMS %FS | P10 RMS %FS | Max RMS %FS | Peak %FS | Spike windows | Dropout windows |
|---|---:|---:|---:|---:|---:|---:|
| Quiet | 0.1241 | 0.1210 | 0.2033 | 0.8698 | 0 | 0 |
| Cable gently wiggled 5 cm from pickup | 0.3836 | 0.1397 | 6.1443 | 26.4435 | 58 | 0 |
| Pickup-end plug gently rotated/wiggled | 0.3747 | 0.1218 | 3.9304 | 10.7147 | 55 | 0 |
| UM2 INST 2 plug gently rotated/wiggled | 0.9017 | 0.3284 | 4.5487 | 22.0032 | 140 | 0 |
| Pickup housing lightly squeezed from sides | 0.3432 | 0.1634 | 1.9320 | 3.5706 | 46 | 0 |

Verdict: **UNCLEAR**, not proof that the piezo is faulty and not a clean bill
of health for the cable/connectors. All manipulations generated threshold
crossings, with UM2-end manipulation showing the most. But cable/plug movement
can transmit mechanical vibration and housing squeezing directly stresses a
piezo. Recorded RMS/peak CSVs alone cannot distinguish that response from
electrical crackle; raw waveform/audio was not saved. Zero low-floor dropout
flags also cannot exclude an intermittent signal connection hidden by the
interface noise floor. No audible crackle observation was supplied.

Single next diagnostic, only when A is ready: substitute a known-good compatible
1/4-inch TS cable and repeat the same gentle UM2-end plug manipulation at the
same gain/mounting. Compare with this result, keeping cable handling as similar
as possible. This is a proposed cable A/B test, not performed or authorized to
execute automatically now. Improvement would implicate the original cable/plug
assembly; persistence would still require separating UM2 jack/contact effects
from transmitted vibration. Do not replace the pickup based on these five runs.
The earlier pressure-response conclusion below remains evidence for a
pressure-sensitive mechanical/contact state, not exclusion of electrical faults.

## Previous: October 19 night coupling check and October 20 restart plan

This section supersedes the older plan to reuse old knock/neutral and merely
finish two scratch holdouts. Stop collection and tuning tonight. No gain, gate,
mounting, paper pad, audio or FFT settings were changed during this check;
the third condition alone applied temporary light finger pressure to the pickup.
No training, holdout or trial data were collected. All earlier data are preserved.

Diagnostic run set: `measurements/coupling_check_20261019/`, never for training.
Three device_check runs, each 10 s, 200 non-overlapping 50 ms windows, WASAPI
USB Audio CODEC index 15, stereo ch2 at 48 kHz, gain A. Every run complete,
zero overflow blocks and zero measured clipping. Hardware CLIP-lamp observation
was not supplied for these runs; do not invent it.

| Condition | Median RMS % FS | P10 RMS % FS | Peak % FS |
|---|---:|---:|---:|
| Three hardest knocks, knock zone | 0.1176 | 0.1152 | 44.293 |
| Normal center-paper scratch, pickup untouched | 0.1181 | 0.1153 | 16.214 |
| Same scratch, other hand lightly pressing pickup down | 0.6491 | 0.3728 | 3.766 |

Verdict under A's specified rule: **COUPLING LOOSENED**. Pressing raises median
scratch RMS 5.49x (14.80 dB) and P10 3.24x (10.20 dB), despite the maximum
transient peak being lower. Knock peak matches the prior 44.3% FS result and
is below another earlier 58.9% FS reference; the knock comparison alone does
not show attenuation. The strong pressure response supports a coupling/contact
problem. It does not prove historical loosening or rule out a simultaneous pad
issue: finger pressure can change mechanical loading, and actions were manual.
Do not train with the finger-pressed diagnostic or require finger pressure in use.

Earlier same-setup path check: GUI quiet median/P10 0.11794/0.11435% FS versus
device_check 0.11829/0.11493% FS. Both paths recorded weak scratch; no fixed
background-level scaling error was found. Device_check normal median 0.12553%
FS despite overall RMS 0.34653% FS, showing transient-dominated energy.
GUI diagnostics are under `data_sessions/diagnostics/gui_level_check_20261019/`;
sounddevice comparison is `measurements/paired_path_check_20261019/`.
All are diagnostic only and excluded from training/holdout/trial evaluation.

### Tomorrow: Tuesday October 20 (America/Los_Angeles)

1. **Re-mount and freeze a NEW setup.** Put double-sided tape under the pickup's
   sensing face and tape over its top. Replace the paper pad with a fresh sheet
   fully adhered to the board, not taped only at the edges. Then record the actual
   new mounting, paper, locations and photographs as a new frozen setup in
   `SETUP.md`, using a new setup ID/session root. These physical changes and
   SETUP update are planned, NOT performed tonight. Keep gain A and all frozen
   Windows/audio/capture/FFT/feature settings unchanged.
2. **Acceptance through the GUI recording path.** Record diagnostic quiet,
   light scratch, normal scratch and hard knock. Aim for scratch median at least
   about 0.3% FS and hardest-knock peak below about 70% FS, with no clipping.
   Confirm actual levels before starting formal collection. Do not substitute
   device_check acceptance for the training/live GUI path.
3. **Re-record ALL data under the new setup in one session.** Collect training:
   10 knock, 10 scratch (label remains `rub`), 16 neutral; then explicitly confirmed
   holdout: 2 per class; then 20 development trials. Give exact actions and wait
   for actual results one recording at a time. Mark EVERY previous session as a
   different setup in selection metadata/documentation and exclude it from new
   training, including previously reusable knock/neutral. Never delete or rewrite
   old raw captures. Do not pool pressed diagnostics or earlier setup data into
   new training. Keep holdout and development trials outside training exports.
4. **Retrain and deliver.** Use only the new setup's training data; derive gate
   thresholds again from new data, compare/tune using grouped training validation
   and development trials, and tune smoothing on those trials. Keep holdout out
   of selection. Freeze parameters, record 8 fresh test trials for final evaluation,
   then hand the model file and matching decision-parameter file to B. Report
   actual final results and limitations. NPZ/ZIP delivery remains via cloud, not Git.

Pending GUI diagnostic support and the Dear PyGui class-list enable/disable fix
were verified with 23 tests, including real GUI widget start/stop and diagnostic
NPZ saving (synthetic test input, not a physical measurement). Diagnostic labels
are excluded from training/default export/QA selection. No signal processing or
gate changes are part of that fix. Work remains on `a-tuning`; preserve B's branch.

## Historical progress below (superseded where it conflicts with the restart plan)

**October19 model ownership / pre-grid update:** A now owns retraining/tuning on
`a-tuning`, based on B's `model-training` branch. B's v1 used OLD fingertip rub.
See `docs/PREGRID_FINDINGS.md`: train-only five-fold grouped comparison slightly
favors 8 kHz (macro F1 73.86%; 12 kHz 73.85%). B's OR energy gate rejects 90.74%
of accepted scratch training windows, including 92.21% of light windows. No
actual trials exist to check cutoff performance or single-knock runs yet.
Lower gate thresholds and knock K=1 must be included in subsequent tuning.
No new holdout scoring or full parameter grid has run. Latest recording plan:
two scratch holdouts, twenty development trials, then eight fresh final trials.
This supersedes the earlier eight-development-trial reduction and B ownership.

**CURRENT v2 (October18):** `rub` label now means scratch_nail_paper. Feasibility
passed: light/normal scratch98.5%/100% of50ms windows above quietP95, vs old73%;
P10 contrasts4.79/5.90dB vs old-0.18dB. Main benefit is consistency, not median.
Hard knock44.296%FS/no clip or overflow; signal feasibility only.
See docs/scratch_v2.md. A recorded11 scratch train takes; explicit later-duplicate
exclusion selects10 with only2 light. Original take/config/logs unchanged.
Holdout confirmation modal and evaluation-only8s trial capture implemented;
trial_replay.py supports B adapter/policy and SET scoring. Real two scratch
holdout + twentytrial captures, combined QA/replay and v2 ZIP remain pending.
Old rubs excluded by current QA selection; old knock/neutral retained and drag
neutral flagged. Previous51.5%/70.2% results are historical, not v2 results.
All sampling/FFT/features unchanged. Nineteen tests pass; updated GUI requires
operator live check. Paper pad size3x5cm confirmed; stock/coordinates pending.

**DELIVERY UPDATE:** large binary upload retries stopped at A's request after
HTTP 408. Remote history through f655944 is unchanged. Only the unpublished data
commit was removed, with local files retained. Final-session and handoff NPZs
are ignored by Git; small logs/config/QA/code/docs remain tracked. Data is packaged
as `packages/A_final_20261017_195725_85cb47b5.zip`, to be shared by A's cloud link
(pending). See HANDOFF_B.md and docs/cloud_archive.json. No cloud upload performed.

**AUTHORITATIVE FINAL DATA UPDATE (supersedes pending-collection text below):**
43 original takes collected, all A, in `data_sessions/20261017_195725_85cb47b5/`.
Actual live GUI autosave/counters worked. Intended holdout notes were entered but
Data split stayed train. Seven explicit take-ID corrections are applied ONLY in
derived exports, preserving raw NPZ/logs. Use
`handoff/20261017_195725_85cb47b5_review1/README.md` as current B/Claude handoff:
36 train takes (10 knock/10 rub/16 neutral; 19095 rows), 7 holdout
(2 knock/2 rub/3 neutral; 3732 rows), all 1200 features. Extra holdout neutral and
20.297 s neutral drag take retained. Never train from current GUI/raw split tags.

`qa_dataset.py` implemented and run: grouped CV by take, log1p/StandardScaler/
LinearSVC fitted inside folds; holdout excluded from fitting. Grouped window
accuracy 51.51%; holdout 70.18%. Every held-out take had all three labels in its
raw predicted set; these are not formal SPACE trials, and reliable bakeoff
performance is NOT established. Quiet P95=0.2223%FS; 10/12 rub medians at/below it.
Two training knock peaks reached 74.115/72.763%FS. No automatic exclusion based
on those flags. See QA.json/CSV for take IDs (actual JSON filename qa_report.json).
13 regression tests pass, including raw immutability, split correction and
holdout/fold isolation. No capture/FFT/features changed.

A's capture and software/data handoff portion is ready with documented risks.
Remaining physical documentation: setup photos, measured sensor/zone coordinates,
thickness and cable restraint; no stranger/second-table validation. B owns final
model, gate/smoothing, SPACE recorder and B/C integration. Fresh independent
trials are needed after model development; do not iterate on the reviewed holdout.

**FREEZE CONFIRMED:** A restored original gain from mark/photo, hardware CLIP did
not flash, board directly on table without padding. Solo plan is
`docs/solo_collection.md`: 36 train + 6 holdout takes, all performer A. GUI
`--final` marks new final sessions, saves split per take/exported row and displays
per-class take counts; holdout never enters GUI fitting. Existing data is pilot.
Eleven regression tests pass; controls build and split toggles in an audio-free
check, but automatic native GUI setup/teardown did not complete successfully.
Full live GUI confirmation is pending operator launch. No FFT changes.

**LATEST UPDATE:** four zone checks pass digital criteria. Board 17 x 27 cm;
actions ON separate bandages (nearest pickup=RUB, farther=KNOCK), not bare board.
Firm median contrast 16.67 dB; hard peak 58.868% FS; zero digital clipping/overflow.
See `docs/zone_check_results.md` for values and pending physical confirmations.
This supersedes older pending-zone statements below. Final/holdout and QA remain.

**A's complete assignment is NOT finished.** Capture tools and pilot upload are
complete; final hardware freeze, solo final/holdout collection and dataset QA remain.
Do not describe the existing data as final or bakeoff-validated.

Repository: https://github.com/FleabagEE/backoff-project (`main`). Reviewed capture/
calibration commit: `290392b`. Local workspace was clean and that commit matched
GitHub when this report was prepared. This report itself adds documentation only.

## Completed and already uploaded

- UM2 INST 2 -> USB -> WASAPI USB Audio CODEC; stereo int16, select ch2.
- Existing settings preserved: 48000 Hz, 480-frame/channel capture block,
  2400-sample/50 ms FFT, original feature processing, 1200 full-spectrum amplitudes.
- Windows input level 100, enhancements OFF, +48V OFF. Operator confirms no CLIP
  flashes in reported calibration runs. Device index was 15 but must be rechecked.
- Repaired PyAudio channel selection and continuous GUI update/collection.
- Per-take autosave, performer/variation notes, 25 s auto-stop, recoverable export.
- Ten regression tests passed after the diagnostic extension; subsequent changes
  were measurement/documentation commits, with no feature-pipeline changes.
- Pilot session `data_sessions/20261017_013429_24eda79c/` is on GitHub, including
  `dataset.npz`, individual take archives, CSV log and configuration snapshot:

| Class | Takes | Feature rows |
|---|---:|---:|
| neutral | 2 | 1066 |
| knock | 1 | 534 |
| rub | 1 | 533 |

Total **4 pilot takes, 2133 x 1200** finite features, all performer A. No raw WAV.
The two neutral metadata notes both say quiet background; the intended talking/
typing action in the second take was never confirmed. No held-out test takes exist.

- `measurements/rub_ab_summary.csv` and `rub_ab_intervals.csv` contain **16 recorded
  calibration runs** (not 16 accepted results). One missed-knock attempt is excluded
  in `rub_ab_exclusions.csv`; all five C runs are now excluded from board-rub
  comparison, with original files and labels preserved.
- Full run IDs, observations and dB calculations: `docs/rub_margin_ab.md`.

## Exploratory results and corrected interpretation

Contrasts use median or P10 of 50 ms PCM RMS divided by that configuration's quiet
median, expressed as `20 log10(ratio)`. They are level contrasts, not classifier
accuracy or a signal-only SNR measurement.

| Recorded option | Light-rub median contrast | Light-rub P10 contrast | Hard-knock peak |
|---|---:|---:|---:|
| A original gain | 10.19 dB | 5.09 dB | 22.97% FS |
| B raised gain, step 3 | 9.21 dB | 5.23 dB | 47.09% FS |
| C pickup/restraint contact: INVALID for board rub | 6.21 dB | 2.28 dB | 25.09% FS |

The latest explicit instructions retire the 15 dB target. Original gain A is the
selected starting configuration, pending identification/restoration from an actual
mark or photo: B did not improve light-rub contrast and left less knock headroom.
A/B rubbing locations may also have included the pickup vicinity, so these are
exploratory observations, not accepted measurements of the final marked zones.
Do not infer gain or bandage causality from single manually performed runs.

**Corrected operator facts:** C rubbing contacted the red pickup/white restraining
bandage, rather than the intended bare-board rub area. This latest explicit
correction supersedes the earlier ambiguous bare-board reply. All C runs are
invalid for board-rub comparison; companion exclusions record this without
rewriting raw data. **Keep the pickup's mounting bandage unchanged.**

No new zone-check measurements exist yet. See `docs/zone_check.md`: at original A,
measure marked bare-board quiet/light rub/firm rub/hard knock. Freeze if firm-rub
median contrast is approximately >=10 dB, hardest knock <=approximately 70% FS,
no clipping and no capture loss. Otherwise make one likely physical correction
and repeat once. Light-rub P10 contrast near 5 dB argues against a high energy
gate; use clear, practiced firm-fingertip instructions and mostly medium/firm data.

## Still required, in order

1. Obtain actual board dimensions, pickup coordinates and an original-A gain
   reference. Mark separate bare-board KNOCK/RUB zones, away from pickup/bandage,
   then run the four-condition zone check. Do not guess A's knob position or
   remove mounting tape. Wait for operator measurements before accepting setup.
2. Freeze/document board dimensions, sensor coordinates, rub/knock zones, gain mark/
   photos in `docs/setup/`, mounting, cable strain relief and padding. Verify final
   level ranges, after-replug process and two-minute pre-collection/demo checklist.
   Current physical dimensions/photos/padding are incomplete.
3. Replace the older three-person schedule with A-only varied collection: at least
   **10 knock + 10 rub + 16 neutral training takes**, 25 s each, interleaved by class.
   Then record LAST **2 held-out takes per class**, explicitly flagged holdout.
   Minimum total **42 final takes** (36 training + 6 holdout). Do not count pilot
   takes toward this target. Add variation presets/progress support if useful.
4. Implement `qa_dataset.py` (currently absent): per-take/class/variation counts,
   suspicious-level flags and silent-window fractions based on quiet takes;
   log-magnitude + StandardScaler + LinearSVC sanity baseline with GroupKFold by
   take ID, holdout excluded from fitting and used for final QA evaluation only.
   This is QA, not B's final model.
5. Update SETUP/HANDOFF with actual final session IDs, pilot/final/holdout status,
   measured ranges, QA results and an evidence-based energy-gate recommendation.

B still owns production model, gate/temporal decisions, SPACE trial-set recorder
and B/C slide integration. No completed end-to-end bakeoff trial evaluation exists.

## Constraints for continuing

- A holds all hardware and is the sole performer. Give exact physical actions and
  commands, then WAIT for actual results. Never invent measurements.
- Do not change sample rate, capture block, FFT size/window or feature processing.
  Recommendations for B only: possible <16 kHz/log features, existing 20 Hz plot
  axis offset after DC removal, cadence-dependent smoothing (~21 updates/s measured).
- Never delete data; keep pilot/different setups separate and explicitly labelled.
- Run `uv run python -m unittest -v test_collection` before and after code changes.
  Make small commits; push main only after relevant tests pass.
