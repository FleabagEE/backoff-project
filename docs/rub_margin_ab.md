# Task 1: operator-guided rub margin comparison

## Authoritative correction and decision (latest user instructions)

This section supersedes the historical recommendations below. **C rubs were on
the red pickup / white mounting restraint, not the board.** Preserve C files and
original labels, but mark the entire C run set INVALID for board-rub comparison
(pickup-contact rubbing). Quiet/hard-knock numbers remain technical observations,
not validation of a proper C board-rub protocol. Companion exclusions identify runs.
This latest explicit correction supersedes the earlier ambiguous bare-board reply.

Keep the pickup bandage/mounting unchanged. Do not remove a presumed rub-zone patch.
The **15 dB light-rub goal is retired**. User selects **original gain A** instead of
B: B did not improve recorded rub contrast but increased tested knock peak. Physical
restoration to A must be confirmed against its actual mark/photo; no position is
invented from approximate prior knob rotations. A/B rub locations may also have
contacted the pickup: treat all old comparisons as exploratory, not final acceptance.

Next: measure board dimensions/coordinates, define isolated bare-board KNOCK/RUB
zones, then perform `zone_check` at restored A gain. Firm-rub median contrast
>=about 10 dB and hardest knock <=about 70% FS, with no clipping, permits immediate
freeze. Otherwise one physical fix/retest only. Details: `docs/zone_check.md`.
Medium-to-firm rub instruction and final-data QA will address weak light-rub risk;
do not change the feature pipeline or present old numeric goals as still binding.

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
| B gain, step 3 candidate | 0.1198119 | 0.3459591 / 0.2186900 | 9.21 / 5.23 | 0.4104691 | 47.0947266 | measured; light-rub target unmet; operator confirms no CLIP flashes |
| C pickup-contact protocol (INVALID for board-rub comparison) | 0.1206081 (retry) | 0.2464201 / 0.1568561 | 6.21 / 2.28 | 0.4510998 | 25.0915527 | preserve only; rubs contacted pickup/restraint |
| D closer, optional | n/a | n/a | n/a | n/a | n/a | skipped: operator reports pickup already very close to rub area |

Historical comparisons below are retained for audit. Current decision is **restore
original gain A and run marked-zone checks**, as specified above; B recommendation
and 15 dB acceptance statements in older chronological notes are superseded.

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

### Gain candidate B light rub

Run `b1b4608a5621`, `B_gain_rub_light`, 2026-10-18T00:09:56Z
(October 17, 17:09:56 America/Los_Angeles), gain note `A_plus_12deg`.
Complete 10.00 s, 200 windows, zero overflow and zero digital clipping. ch2 median
RMS **0.3459591% FS**, P10 **0.2186900% FS**, overall RMS **0.4371521% FS**,
maximum peak **3.0883789% FS**. Against B quiet, median contrast is **9.21 dB**
and P10 contrast **5.23 dB**. Median target 15 dB is not met; A's corresponding
values were 10.19 / 5.09 dB. These single hand-performed runs do not establish a
causal gain effect or monotonic improvement. Finish B normal rub at unchanged gain,
then test the textured rub-zone option instead of chasing amplitude with more gain.

### Gain candidate B normal rub

Run `89ed8d26fbb2`, `B_gain_rub_normal`, 2026-10-18T00:13:28Z
(October 17, 17:13:28 America/Los_Angeles), gain note `A_plus_12deg`.
Complete 10.00 s, 200 windows, zero overflow and zero digital clipping. ch2 median
RMS **0.4104691% FS**, P10 **0.2140613% FS**, overall RMS **0.4614996% FS**,
maximum peak **2.2186279% FS**. Against B quiet, median contrast **10.70 dB**,
P10 contrast **5.04 dB**. B quiet/light/normal/hard-knock runs are now measured,
though the hard-knock CLIP LED report remains pending. The light-rub target is unmet.

Next C preparation: keep the B step 3 gain, sensor position/mount, padding and
rub location fixed. Add a small firmly attached sandpaper/textured-tape patch on
the EXISTING rub area (not over the pickup), without a soft foam backing. Obtain
A's material, patch dimensions and placement/photo before starting C measurements.
Texture is the only intended variable. C is a different physical setup; existing
session data remains pilot. No final hardware choice or classifier performance is
established by this B result.

### C material preparation and provisional quiet run

A reported attaching an **OK adhesive bandage** at the existing rub location.
Keep B step 3 gain and the existing sensor mounting. Exact bandage material,
dimensions, cloth-versus-pad rubbing face and placement photo remain unreported;
do not equate it with rigid sandpaper or assume its effect before testing.

Run `497d965d085f`, `C_bandage_quiet`, 2026-10-18T00:23:24Z
(October 17, 17:23:24 America/Los_Angeles), gain note `A_plus_12deg`:
complete 10.00 s, 200 windows, zero overflow and zero digital clipping. ch2 median
RMS **0.1664591% FS**, P10 **0.1212363% FS**, overall RMS **0.6377800% FS**,
max peak **5.2124023% FS**. Median is 2.86 dB above B quiet. The first report has
RMS 2.2441% FS and later reports fall substantially (last interval ~0.1294% FS).

Capture is technically complete, but the intended quiet condition/stability is
not yet confirmed. Preserve this run as **provisional**, not the accepted C quiet
reference or evidence that the bandage causes noise. Repeat unchanged setup as
`C_bandage_quiet_retry1`, hands off board/cable/interface for the full run, and ask
A whether there was contact/movement in the original run. If actual environmental
noise persists, record it rather than selectively discarding difficult quiet data.

### C bandage quiet stability retry

Run `be9668eb7789`, `C_bandage_quiet_retry1`, 2026-10-18T00:38:30Z
(October 17, 17:38:30 America/Los_Angeles), gain note `A_plus_12deg`.
Complete 10.00 s, 200 50 ms windows, zero overflow and zero digital clipping.
ch2 median RMS **0.1206081% FS**, P10 RMS **0.1144196% FS**, overall RMS
**0.1223143% FS**, maximum peak **0.5798340% FS**. This is close to B quiet
(median difference **0.06 dB**) and is selected as the C comparison quiet reference.
The first C quiet run remains preserved/provisional; A has not identified its
transient cause, so no attribution is made. At this reference, a 15 dB median
rub contrast requires approximately **0.6782% FS** light-rub median RMS.

Next measure `C_bandage_rub_light` on the bandage at unchanged gain/mount/position,
using the same naturally light finger pressure as A/B. Patch dimensions, exact
rubbing face and placement photo still need documenting before hardware freeze.

### C bandage light rub

Run `6428cf75b4f1`, `C_bandage_rub_light`, 2026-10-18T00:43:05Z
(October 17, 17:43:05 America/Los_Angeles), gain note `A_plus_12deg`.
Complete 10.00 s, 200 windows, zero overflow and zero digital clipping. ch2 median
RMS **0.2464201% FS**, P10 **0.1568561% FS**, overall RMS **0.8916925% FS**,
maximum peak **8.2031250% FS**. Against stable C quiet retry, median contrast
**6.21 dB**, P10 contrast **2.28 dB**. These are below B's 9.21 / 5.23 dB in the
single recorded light-rub runs and below the 15 dB median target. Higher overall
RMS/peak does not establish sustained rub separation when median/P10 remain low.
Do not conclude causality from one uncontrolled hand-performed comparison; document
the actual bandage face/placement and finish normal rub before deciding the option.

### C bandage normal rub

Run `b4f282817f1f`, `C_bandage_rub_normal`, 2026-10-18T00:45:54Z
(October 17, 17:45:54 America/Los_Angeles), gain note `A_plus_12deg`.
Complete 10.00 s, 200 windows, zero overflow and zero digital clipping. ch2 median
RMS **0.4510998% FS**, P10 **0.1663760% FS**, overall RMS **1.2592917% FS**,
maximum peak **8.1054688% FS**. Against C quiet retry, median contrast **11.46 dB**,
P10 contrast **2.79 dB**. Normal-rub median exceeds B's recorded normal-rub median,
but weaker intervals remain poorly separated and light-rub target remains unmet.
Finish `C_bandage_knock_hard` at the same gain/location and report CLIP before
comparing completed configurations. Bandage rubbing face, dimensions and photo
remain unreported; do not freeze this setup or assume texture has solved rub.

### C bandage hardest knock and comparison status

Run `2cd2d668ef87`, `C_bandage_knock_hard`, 2026-10-18T00:49:02Z
(October 17, 17:49:02 America/Los_Angeles), gain note `A_plus_12deg`.
Complete 10.00 s, 200 windows, zero overflow and zero digital clipping. ch2 maximum
peak **25.0915527% FS**, overall RMS **4.4819807% FS**, median 50 ms RMS
**0.5335157% FS**, P10 **0.1191134% FS**. A did not report CLIP LED status.

A/B/C numeric comparisons are complete. Light-rub median/P10 contrasts are
**A 10.19/5.09 dB, B 9.21/5.23 dB, C bandage 6.21/2.28 dB**: no option reaches
15 dB. C's tested hard knock is below 70%, but its lower peak than B at nominally
unchanged gain may reflect uncontrolled force/position or setup differences, not
proof of a bandage effect. No causal conclusion or final freeze is justified.

Next obtain a full-board photo showing pickup, bandage/rub area and knock area,
with their separation/dimensions, before deciding whether an optional closer-sensor
test is useful. Do not blindly move the pickup or increase gain. Confirm the actual
bandage rubbing face and outstanding CLIP report during this setup inspection.
Original data/measurements remain intact, all old collection sessions remain pilot.

### Operator follow-up: proximity and CLIP status

A reports the pickup is already very close to the rub zone, and **CLIP never
flashed during the reported tests**. This resolves the earlier pending CLIP reports
for the gain/bandage comparisons; historical notes above describe what was known
when each measurement arrived. Exact sensor/rub coordinates and dimensions remain
unmeasured, so do not invent a numeric distance.

Skip optional D (moving closer) rather than disturb an already close mounting.
Gain and sensor stay unchanged for now. Confirm whether sandpaper or a textured
tape patch is available: the tested OK bandage is a distinct candidate, with
rubbing face/padding still unspecified, and cannot stand in for a measured
sandpaper/textured-tape result. If unavailable, document the unmet 15 dB target
and choose a reproducible measured compromise; never claim the target was met.

### Available-material decision and next hardware documentation

A reports **no sandpaper, anti-slip tape or other thin textured tape is available**.
Do not require a purchase or repeat gain-only experiments. Optional closer-sensor
test is already skipped because A reports the pickup is close to the rub zone.

Recommend restoring **B bare-board configuration at the current step 3 gain**:
remove only the newly added OK bandage from the rub area, preserving pickup mounting
tape, cable strain relief, gain and all Windows/capture settings. This is a
provisional instruction; restoration has NOT yet been confirmed by A.

Rationale: B's tested hard-knock peak 47.09% FS leaves headroom and its light-rub
median/P10 contrasts 9.21/5.23 dB exceed the bandage run's 6.21/2.28 dB. A's median
contrast was slightly higher (10.19 dB), so B is NOT proven superior to A for rub;
the higher tested gain/current reproducibility is a practical compromise. Force,
position and single-run variability limit causal comparisons. None meets 15 dB.

Remaining risk: weak/variable light rub may be gated as neutral; an energy threshold
alone may not separate all neutral adversaries from rub. Preserve original features
and measure silent-window fractions/grouped QA before treating this as usable final
training data. No claim of bakeoff trial reliability is warranted yet.

Task 1 measurements/available-option comparison are complete with target unmet.
Task 2 is pending: A must confirm restoration, supply board/sensor/rub/knock/padding
dimensions and gain/mount photos, then perform a short restored-setup level check
before the configuration can be marked frozen. No final/holdout collection yet.

### Photo clarification required: do not remove the pickup restraint

A supplied a photo showing one white adhesive bandage crossing the red pickup
housing and attaching to the board. This is visibly a **pickup restraint**; the
photo does NOT establish a separate textured patch in the board's rub zone.
The earlier instruction to remove a presumed separate rub-zone bandage is therefore
**withdrawn pending clarification**. Do not remove the photographed pickup restraint,
move the sensor, or declare B restored. No physical removal is confirmed.

Ask A to identify where the C rub tests were performed: adjacent bare board,
the bandage/pickup housing, or a separate patch not shown. Until confirmed, A/B/C
numeric results remain preserved but the physical interpretation of C is pending;
do not claim a controlled added-texture comparison. If C involved rubbing the
pickup itself, it is not the intended board-rub condition and must not be used as
evidence for board-rub performance. Never silently relabel or delete those runs.
