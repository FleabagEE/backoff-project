# Final v3 event-style collection and early checkpoint

Latest A request supersedes the incomplete six-take mini-pilot plan. Start the
full collection under unchanged `A_wood30x30x6_v3_candidate2`, with an EARLY
CHECKPOINT after two interleaved K/R/N rounds. This is explicit authorization
to proceed despite earlier failed level targets; it is not a claim those targets
passed. No new hardware, gain, sample rate, FFT or feature processing change.
The earlier durability check remains unperformed; do not invent a result.

## Selection and pilot audit

Only the single NEW folder created under `data_sessions/final_v3/` is eligible
for final training/evaluation. Require session_type final, the candidate2 setup
ID and event-style metadata for positive takes. All prior sessions, including
`data_sessions/pilot_wood/20261019_130420_b7d74cb6`, are excluded and retained.
See `pilot_wood_exclusions.csv`: five existing pilot takes have matching class
and notes (K1,K2,R1,R2,N1 quiet); mixed-neutral N2 was never recorded. First K
is take/train; remaining four diagnostic/diagnostic. That is a recording-type
inconsistency, not a class/notes mismatch. Do not edit/relabel raw files.

## New recording style

Use GUI `take`, split `train`, 25s, --event-rhythm, ONE GUI session for all
training, holdout, development trials and later supplemental takes. Session root
is final_v3, not pilot_wood. Do not close/relaunch it between blocks unless needed
for a fault; never silently start a second source session.

Positive cues at 1,3,5,...,23 seconds = 12 actions. Knock once at each KNOCK NOW;
scratch back-and-forth for about 1s at each SCRATCH NOW; stay still between cues.
Cue is visual only (no beep to contaminate measurements). No hand on pickup,
mounting tape or cable. After recording, save raw take-level labels, timestamps,
RMS/peak and expected-event metadata. Raw take labels are NOT final per-window
training labels. The GUI's raw Train Model button is disabled in event mode;
training requires the offline selected-window pipeline.

First two rounds (pause after six):

| Round | Class | Variation notes |
|---|---|---|
| 1 | knock | r01_knock_medium_right_center |
| 1 | rub | r01_scratch_nail_wood_normal_right_index_center |
| 1 | neutral | r01_neutral_quiet |
| 2 | knock | r02_knock_medium_right_center |
| 2 | rub | r02_scratch_nail_wood_normal_right_index_center |
| 2 | neutral | r02_neutral_mixed_palm_fingertip_typing_object_dragging |

Neutral quiet: hands off/no talking/typing. Mixed: about5s each palm pats,
fingertip taps, nearby laptop typing, placing/lifting an object, dragging that
object; record actual object/action notes, no knuckle knock or nail scratch.
The six raw takes count toward the final training target ONLY if A continues
after the checkpoint. No pilot takes are substituted. After continuation, keep
interleaving toward K10/R10/N16 with the originally requested variations, then
six confirmed holdouts and twenty8s development trials. Trials remain separate
from training. Fresh eight test trials only after model/parameters are frozen.

## Offline segmentation and energy gate

`event_segmentation.py` computes a 0.5–8 kHz energy proxy from saved FFT X after
undoing known pink weighting; correct saved-bin frequencies start at20Hz.
Temporal smoothing already in X is retained; this is not raw PCM band energy.

Reserve the FIRST5s of the NEW round1 quiet take for calibration. Exclude this
prefix from both classifier fitting and scored windows in BOTH checkpoint folds,
so the gate is not calibrated on scored test data when round1 becomes test.
The remaining quiet is an ordinary neutral training/test take as appropriate.
No old diagnostics or pilot quiet are used for calibration.

Fixed initial gate = quiet P95 band energy. Detector onset threshold=max(1.25x
quiet P99,1.5x quiet P95), release=quiet P95; minimum quiet rearm .15s, refractory
1.7s. These are starting rules, not tuned on checkpoint test labels. Each detected
onset gets context[-.2,+1.5]s. Mark incomplete edge segments; do not pad them or
invent events. Report detected and complete event counts against expected12,
onset times and retained/dropped window counts for EACH positive take.

Positive classifier FIT windows must lie in a complete detected event AND exceed
the quiet-derived gate. Drop all other windows from K/R fitting (do not label
silence K/R); retain all neutral fit windows except reserved calibration prefix.
Keep complete raw timelines and context for evaluation/replay. Do not hide missed
actions by reporting accuracy only on above-gate windows.

Initial inspection after quiet is available:

```cmd
uv run python event_segmentation.py data_sessions/final_v3/ACTUAL_SESSION --quiet-take-id ACTUAL_QUIET_TAKE_ID --output handoff/NEW_EVENT_INSPECTION.json
```

## Six-take checkpoint (not run until real six takes exist)

Fixed B pipeline: <=8kHz -> log1p -> StandardScaler -> balanced LinearSVC C=.001.
Fit round1, test round2, then swap; scaler/model only fitted on training fold.
Report fold accuracies and their arithmetic mean, pooled confusion matrices,
balanced accuracy, each class recall, scratch->neutral rate; repeat with energy
gate forcing below-threshold outputs neutral. No smoothing or parameter search
at this checkpoint. Calibration prefix excluded as described above.

Per-window evaluation must include inter-event silence as NEUTRAL, not the
whole-take positive label. Predeclared cue-based reference: 1s after each rub cue,
and .35s after each knock cue, is the expected positive action interval;
remaining timestamps are neutral. Actual human timing may differ, so explicitly
call these approximate labels. Report detected-context/active-window metrics
separately; do not use the same energy gate to define the only scored positive
ground truth. This prevents below-gate missed scratches disappearing from the
denominator. Show event counts/cue alignment and diagnose timing mismatch if any.

A's continuation goal is about>=90% accuracy with scratch rarely neutral
(predeclared <=5%). Report no-gate AND gated outcomes and poor class recall even
if overall accuracy is high due to quiet windows. If failed, stop and describe
confused classes plus ONE recommended fix, then wait for A. Do not silently
change the gate or select a better test fold to pass. Neutral round1 quiet vs
round2 adversarial distribution differs substantially; this is limited evidence,
not final bakeoff validation.

## Development-trial comparison later

On the twenty development trials compare (a) per-window gate+smoothing+
hysteresis/cooldown versus (b) detected-event classification via mean multiclass
decision score (helper event_decisions) or majority vote. Reset state each trial;
score entire predicted SET including quiet onset/tail and incomplete end events.
Choose by passes, then fewer non-neutral negative outputs. Never tune on the
six holdouts or eight fresh final trials. Report event counts/failures; detector
misses and false detections remain part of trial performance.
