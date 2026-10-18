# Teammate A progress report — October 17, 2026 (America/Los_Angeles)

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
  in `rub_ab_exclusions.csv`; the first C quiet run is preserved as provisional.
- Full run IDs, observations and dB calculations: `docs/rub_margin_ab.md`.

## Rub-margin results and unresolved interpretation

Contrasts use median or P10 of 50 ms PCM RMS divided by that configuration's quiet
median, expressed as `20 log10(ratio)`. They are level contrasts, not classifier
accuracy or a signal-only SNR measurement.

| Recorded option | Light-rub median contrast | Light-rub P10 contrast | Hard-knock peak |
|---|---:|---:|---:|
| A original gain | 10.19 dB | 5.09 dB | 22.97% FS |
| B raised gain, step 3 | 9.21 dB | 5.23 dB | 47.09% FS |
| C labelled bandage | 6.21 dB | 2.28 dB | 25.09% FS |

No option met the requested 15 dB light-rub target. B is not proven better than A
for rub; trials were manually performed with uncontrolled variation. Do not infer
gain or bandage causality from single runs. A reports no alternative textured
material is available and sensor already close, so no purchase/move was required.

**Important pending clarification:** latest photo shows a white bandage crossing
the red pickup, acting as its mounting restraint. It does NOT establish a separate
bandage patch in the board's rub area. The earlier proposed instruction to remove
the presumed separate patch has been withdrawn. **Keep the pickup restraint.**
A has not yet answered whether C rub was on adjacent bare board, on the pickup/
restraint, or on another patch. Preserve all results, but do not treat C as a valid
controlled texture comparison until answered. If rubbing the pickup itself, it
does not represent intended board-rub interaction.

## Still required, in order

1. Clarify actual rubbing location and unchanged/current physical setup. Do not
   remove mounting tape, change gain or freeze the setup based on assumptions.
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
