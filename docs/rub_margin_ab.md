# Task 1: operator-guided rub margin comparison

Status: **waiting for physical measurements by A**. One performer (A) holds all
hardware. Do not start final collection or freeze gain/mounting until this comparison
is reviewed. No capture/FFT/feature-processing changes are authorized here.

## Measurement method

- Keep 48000 Hz, stereo int16, 480-frame capture blocks; evaluate **ch2**.
- Close the collection GUI first. Run `uv run device_check.py` to find the current
  USB Audio CODEC / Windows WASAPI sounddevice index. It was 15; never assume after
  replugging. +48V OFF, Windows volume 100, enhancements OFF.
- Use 10 s per condition, after the diagnostic's 1 s discarded warmup. Read the
  `MEASURING NOW` prompt. Rub continuously; sample strongest knocks repeatedly.
- `median_window_RMS` and `p10_window_RMS` describe non-overlapping **50 ms PCM RMS**
  windows. The old `median_interval_RMS` uses 500 ms reporting intervals and is a
  DIFFERENT statistic. Do not mix them when calculating margins.
- Summary CSV stores RMS and peak as fractions of full scale (0..1); console prints
  percent FS. Clip percentage is 0..100. `complete` must be True, overflow zero,
  and digital clipping zero before comparing a run. SIG is not the acceptance test.
- Median light-rub margin = `20*log10(light_median_RMS / matching_quiet_median_RMS)`.
  Also report P10 light-rub margin against that quiet median to expose weak intervals.
  These are total RMS level contrasts, not signal-only SNR or classifier accuracy.

## A: current configuration baseline

Before turning any knob, photograph/mark current INST GAIN 2 and mounting. Do not
press the pickup during measurements; touch only the intended interaction zone.
Replace device 15 below if the WASAPI index differs. Run commands separately, then
send the label/SUMMARY and ch2 lines. Give only the FIRST quiet command initially;
wait for that result before guiding the next physical condition.

```cmd
uv run device_check.py --device 15 --rate 48000 --channels 2 --seconds 10 --label A_current_quiet --gain-note current --csv measurements/rub_ab_intervals.csv --summary-csv measurements/rub_ab_summary.csv
uv run device_check.py --device 15 --rate 48000 --channels 2 --seconds 10 --label A_current_rub_light --gain-note current --csv measurements/rub_ab_intervals.csv --summary-csv measurements/rub_ab_summary.csv
uv run device_check.py --device 15 --rate 48000 --channels 2 --seconds 10 --label A_current_rub_normal --gain-note current --csv measurements/rub_ab_intervals.csv --summary-csv measurements/rub_ab_summary.csv
uv run device_check.py --device 15 --rate 48000 --channels 2 --seconds 10 --label A_current_knock_hard --gain-note current --csv measurements/rub_ab_intervals.csv --summary-csv measurements/rub_ab_summary.csv
```

Quiet: do not touch board/cable/interface. Light rub: the weakest realistic rub,
normal rub: repeatable comfortable pressure. Hard knock: strongest intended board
knock with a knuckle, never strike the pickup itself. Preserve position/technique
across configurations. Do not infer a noise floor from a mixed knock/rub take.

## B: gain candidate(s)

Only after reviewing baseline, raise INST GAIN 2 in small measured steps. At each
step test hard knocks first. Seek the highest practical gain with strongest intended
knock <=70% FS and zero clipping, no CLIP indicator/distortion. Back off and repeat
if any hit exceeds the target. Knob angle is not a calibrated dB scale.

At the selected gain repeat quiet/light rub/normal rub/hard knock with labels
`B_gain_quiet`, `B_gain_rub_light`, `B_gain_rub_normal`, `B_gain_knock_hard` and a
gain-note tied to a photo/tape mark. Gain may amplify noise too: measure a new quiet
reference rather than assuming the margin improves.

## C: textured rub zone

At the same gain, attach a fixed sandpaper or textured-tape patch near the pickup;
mark its dimensions/location/material. Do not remount the pickup at the same time.
Repeat quiet, light rub, normal rub AND hard knock using `C_texture_...` labels.
Check comfort, loose edges and whether the action is easy for a stranger to reproduce.

## D: optional closer sensor position

Only if C is inadequate, move the sensor closer to the marked rub zone, preserving
the mounting method. Record old/new measured coordinates and retest all four
conditions under `D_closer_...`. Different mounting/position is a different physical
setup. Old data remains pilot; never silently relabel it as final data.

## Comparison (fill only from A's actual results)

Target: light-rub median at least **15 dB above matching quiet** if achievable;
inspect light-rub P10 as well, with strongest knocks <=70% FS and no clipping.

| Configuration | Quiet median %FS | Light-rub median / P10 %FS | Median / P10 margin dB | Normal-rub median %FS | Hard-knock max peak %FS | Result |
|---|---|---|---|---|---|---|
| A current | 0.1137944 | 0.3679327 / 0.2043900 | 10.19 / 5.09 | 0.3778285 | 22.9675293 | baseline complete; light rub below 15 dB target |
| B gain, step 3 candidate | 0.1198119 | pending | pending | pending | 47.0947266 | quiet valid; rub and hard-knock CLIP report pending |
| C texture | pending | pending | pending | pending | pending | unmeasured |
| D closer, optional | pending | pending | pending | pending | pending | optional |

Recommendation and final ranges remain pending. If target is unattainable, document
the best measured compromise and the residual light-rub false-negative risk for B;
do not change feature processing or fabricate a passing margin.

### Recorded baseline quiet

Run `3f3a26acbad8`, `A_current_quiet`, 2026-10-17T23:12:44Z:
WASAPI USB Audio CODEC index 15, 48000 Hz/stereo int16, gain note `current`.
Measured 10.00 s after 1 s warmup, 200 complete 50 ms RMS windows, zero overflow
blocks and zero digital clipping. ch2 median RMS **0.1137944% FS**, P10 RMS
**0.1118998% FS**, overall RMS **0.1141081% FS**, maximum peak **0.6744385% FS**.
The median is the quiet reference for configuration A, not a mixed-condition take.
At this quiet level a 15 dB median light-rub contrast corresponds to approximately
**0.640% FS** light-rub median RMS. Gain position/photo is still unreported; do not
adjust it before the remaining A runs. Raw interval and run-summary CSVs are in
`measurements/rub_ab_intervals.csv` and `measurements/rub_ab_summary.csv`.

### Recorded baseline light rub

Run `8d5c14decb7c`, `A_current_rub_light`, 2026-10-17T23:25:28Z, same reported
configuration/gain as baseline quiet. Complete 10.00 s, 200 50 ms windows, zero
overflow and zero digital clipping. ch2 median RMS **0.3679327% FS**, P10 RMS
**0.2043900% FS**, overall RMS **0.4538494% FS**, maximum peak **4.0557861% FS**.
Against the recorded A quiet median, the median contrast is **10.19 dB** and P10
contrast **5.09 dB**. The median is below the 15 dB target, and weaker rub windows
have less separation. Normal rub and hardest-knock measurements remain pending;
do not select a final setup or change gain until the A baseline is complete.

### Recorded baseline normal rub

Run `59b4d67412a1`, `A_current_rub_normal`, 2026-10-17T23:39:02Z, same reported
configuration/gain. Complete 10.00 s, 200 50 ms windows, zero overflow and zero
digital clipping. ch2 median RMS **0.3778285% FS**, P10 RMS **0.1759558% FS**,
overall RMS **0.4750260% FS**, maximum peak **2.6062012% FS**. Relative to A quiet,
median contrast is **10.42 dB**, P10 contrast **3.79 dB**. This take's P10 is lower
than the light-rub take: stronger intended pressure did not consistently improve
all windows. Do not assume monotonic rub strength or change gain to explain it;
preserve the observations and finish the hardest-knock reference next.

### Excluded baseline hard-knock attempt (no action)

Run `a1d1fb3d0adf`, `A_current_knock_hard`, 2026-10-17T23:41:53Z: A reported
forgetting to knock. Capture completed, but the physical condition was not performed.
**Exclude this run from hard-knock headroom comparisons**, regardless of its
`complete=True` capture flag. The recorded ch2 peak 0.5798340% FS is background,
not the hardest-knock level. Preserve the original CSV rows. Retry at unchanged
gain under label `A_current_knock_hard_retry1`; all earlier valid quiet/rub runs remain valid.

### Valid baseline hardest-knock retry

Run `eda35a192c78`, `A_current_knock_hard_retry1`, 2026-10-17T23:45:37Z:
complete 10.00 s, 200 windows, zero overflow and zero digital clipping. ch2 maximum
peak **22.9675293% FS**, overall RMS **1.9215047% FS**, median 50 ms RMS
**0.5790114% FS**, P10 **0.1598713% FS**. A confirmed CLIP did not flash.
This supersedes the missed-action attempt for the A hardest-knock comparison.

Configuration A is fully measured. Light-rub median contrast is 10.19 dB (P10
5.09 dB), below the 15 dB target; strongest reported knock leaves headroom relative
to 70% FS. Next measure a modest gain increase, one step at a time, using the same
knock technique/location. Start B step 1 at approximately 10 degrees clockwise from
a photographed/tape-marked A position, and record it as `B_gain_step1_knock_hard`.
Angle is an operator reference, not a predicted gain in dB. Do not raise gain again
until reviewing that run; measure quiet and rub anew at the eventual gain candidate.

### Gain candidate B, step 1 hard knocks

Run `7dbe2e9845d7`, `B_gain_step1_knock_hard`, 2026-10-17T23:48:59Z,
gain note `A_plus_10deg`. Complete 10.00 s, 200 windows, zero overflow and zero
digital clipping. ch2 maximum peak **37.7319336% FS**, overall RMS **6.1847492% FS**,
median 50 ms RMS **1.4063508% FS**, P10 **0.1197435% FS**. CLIP LED status has
not yet been reported; do not infer it from zero digital endpoint clipping.

This measured peak is below 70% FS. If A confirms no CLIP flash, next candidate
is another approximately 5 degrees clockwise (`A_plus_15deg` total), label
`B_gain_step2_knock_hard`, followed by reviewing its strongest peak before any
further gain increase. If step 1 CLIP flashed, do not advance: report it and back
off. Quiet/rub at candidate gain remain unmeasured; no margin improvement is assumed.

### Gain candidate B, step 2 hard knocks (over headroom target)

Run `0026f6ee6edf`, `B_gain_step2_knock_hard`, 2026-10-17T23:51:54Z,
gain note `A_plus_15deg`. Complete 10.00 s, 200 windows, zero overflow and zero
digital clipping. ch2 maximum peak **76.8188477% FS**, overall RMS **6.7506865% FS**,
median 50 ms RMS **1.9398860% FS**, P10 **0.3379431% FS**. CLIP LED status remains
unreported. **This setting exceeds the 70% FS hardest-knock target** and is not
accepted as the candidate gain despite zero digital clipping.

Next back off approximately 3 degrees counterclockwise from step 2, between its
position and step 1 (nominal `A_plus_12deg`). Repeat the same hard-knock condition
as `B_gain_step3_knock_hard`. Operator angles and hand force are approximate:
measured repeated peaks, not angle interpolation, decide acceptance. Photograph
the eventual chosen gain and remeasure quiet/rub there before comparing margins.

### Gain candidate B, step 3 hard knocks (backoff)

Run `7e748ed04fbe`, `B_gain_step3_knock_hard`, 2026-10-18T00:00:35Z
(October 17, 17:00:35 America/Los_Angeles), nominal gain note `A_plus_12deg`.
Complete 10.00 s, 200 windows, zero overflow and zero digital clipping. ch2
maximum peak **47.0947266% FS**, overall RMS **4.7991718% FS**, median 50 ms RMS
**0.2683129% FS**, P10 **0.1318893% FS**. CLIP LED status is still unreported.

This is the highest tested gain-position candidate below the 70% peak target,
not a calibrated proof of the absolute maximum safe gain. Keep this position for
B quiet/light/normal-rub measurements if A confirms no CLIP flash; do not increase
again just to approach 70%. It leaves margin for uncontrolled performer force.
Use `B_gain_quiet`, `B_gain_rub_light` and `B_gain_rub_normal` with the same
`A_plus_12deg` gain note. Compare rub against B's newly measured quiet, not A's
reference. Final gain acceptance and hardware freeze remain pending that comparison.

### Gain candidate B quiet

Run `3c0f5564ab10`, `B_gain_quiet`, 2026-10-18T00:06:01Z
(October 17, 17:06:01 America/Los_Angeles), gain note `A_plus_12deg`.
Complete 10.00 s, 200 50 ms windows, zero overflow and zero digital clipping.
ch2 median RMS **0.1198119% FS**, P10 RMS **0.1145825% FS**, overall RMS
**0.1196073% FS**, maximum peak **0.6744385% FS**. Median quiet is **0.45 dB**
above A's quiet reference. Use this B quiet measurement for subsequent B rub
contrasts; a 15 dB median contrast corresponds to about **0.6738% FS** rub median.
No B rub result exists yet, so gain's effect on rub margin remains unknown.
A has not yet explicitly reported the step 3 hard-knock CLIP LED status.
