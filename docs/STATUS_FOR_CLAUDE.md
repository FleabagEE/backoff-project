# Teammate A progress report — October 17, 2026 (America/Los_Angeles)

## Latest: October 19 night coupling check and October 20 restart plan

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
