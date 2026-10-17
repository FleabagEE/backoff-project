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
| A current | 0.1137944 | 0.3679327 / 0.2043900 | 10.19 / 5.09 | 0.3778285 | pending | quiet/light/normal rub valid; hard knock pending |
| B gain | pending | pending | pending | pending | pending | unmeasured |
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
