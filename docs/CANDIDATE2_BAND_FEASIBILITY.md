# Candidate2 spectral analysis and proposed mini pilot (October 19)

No new recording, model fitting, hardware/gain change or gate change occurred
during this analysis. Four source takes are pinned in `analyze_candidate2_bands.py`.
Results: `handoff/candidate2_band_analysis_20261019/band_analysis.json` and CSV.

## Measurement limits

Saved X is Hamming/rFFT magnitude with DC removed, pink-frequency weighting and
temporal smoothing. We undo the known frequency weighting and sum squared
smoothed magnitudes per band (Nyquist half-weighted). This is a relative band
energy proxy, not recoverable exact unsmoothed 50 ms PCM energy. Absolute physical
band RMS, discarded DC, phase, and noise gain dependence cannot be reconstructed.
The correct saved-bin frequencies are 20,40,...,24000 Hz, not the plot's 0-based
axis. Diagnostics do not alter feature capture or the model's existing input.

Contrasts are 10log10(band energy statistic / quiet median band energy).
Coverage counts saved, overlapping/smoothed windows; they are not independent
trials. Bands are half-open except the final band includes 24 kHz.

| Band | Quiet mean energy share | Normal median/P10 contrast dB | Normal > quiet P95 | Light median/P10 contrast dB | Light > quiet P95 |
|---|---:|---:|---:|---:|---:|
| 20 Hz–<1 kHz | 29.75% | 7.11 / 3.74 | 95.79% | 8.01 / 1.76 | 87.32% |
| 1–<4 kHz | 9.92% | 5.56 / 1.82 | 97.66% | 4.09 / 0.06 | 84.98% |
| 4–<8 kHz | 11.57% | 2.23 / 0.69 | 93.93% | 1.38 / 0.15 | 78.87% |
| 8–<16 kHz | 23.15% | 0.14 / -0.26 | 38.79% | 0.07 / -0.20 | 18.78% |
| 16–24 kHz | 25.61% | 0.14 / -0.09 | 19.63% | 0.09 / -0.17 | 14.55% |

The strongest scratch contrast is below 8 kHz, especially below 1 kHz. These
recordings do NOT support the hypothesis that the distinctive scratch signal is
mostly above 8 kHz. The largest single quiet band is <1 kHz (29.75%), with
40/60 Hz bins contributing about 24.92% of total proxy energy, consistent with
low-frequency electrical pickup/hum but not proof of its source. At 20 Hz FFT
spacing with Hamming leakage, do not distinguish 50 versus 60 Hz from these
bins alone. Broad 8–24 kHz noise together contributes 48.76%; quiet is not
entirely, or mostly by total share, confined to low frequencies.

## Gain and quiet-floor comparison

Hard-knock peak=14.8621% FS. Reaching the earlier 44.3% would require +9.49 dB;
reaching 70% allows +13.46 dB of ideal digital headroom for this measured action.
This is not calibrated knob rotation or a guarantee about harder future knocks
or analog clipping. One fixed-gain spectrum cannot tell whether noise is before
the gain (contrast unchanged) or generated later in the interface (contrast may
improve). The hum component argues against a purely quantization-floor account,
but cannot locate the noise before/after gain. Do not claim a gain increase will
improve SNR. There is amplitude headroom for a controlled gain comparison, but
gain is NOT the first recommended change; preserve candidate2 for the pilot.

Current quiet median=0.129735%, P95=0.146804% FS, versus Sunday feasibility
median=0.118539%, P95=0.123589% FS: about +0.78/+1.49 dB. These are different
times/setup states. Hum pickup, cable routing, table/environmental vibration or
gain/connection drift are possible, not established causes. No evidence supports
declaring a backend scale mismatch from this difference.

## Contrast-based acceptance

Replace the arbitrary absolute broadband 0.3% target with a proposed exploratory
rule: within one fixed reported band, light P10 > quiet P95 and at least 90% of
light windows above quiet P95; normal coverage also at least 90%; knock peak
below 70% FS. Light P10 exceeding the threshold and 90% coverage describe the
same low-tail requirement, not independent evidence. A positive margin would
be preferable; do not silently reduce the 90% threshold after seeing results.

Candidate2 FAILS this rule in all five bands. Best light coverage is 87.32% below
1 kHz, where its P10 is 0.40 dB BELOW quiet P95. The best light P10/quiet-P95
margin among bands is still negative (-0.29 dB at 4–8 kHz). Headroom passes.
Selecting a best band on these recordings is exploratory, not final validation.

## Next action and user-requested classifier check

Do not declare the board unusable or start formal final_v3 collection from these
level metrics alone. The immediate next action is A's requested SIX-TAKE
`pilot_wood` on UNCHANGED candidate2: 2x25s each knock, scratch, neutral. Record
as GUI diagnostic with session_type pilot, under `data_sessions/pilot_wood/`, so
default final training/export excludes it. Explicit mini-pilot fitting may read
only those six identified takes; they never enter final training/evaluation.
Record interleaved K1,R1,N1(quiet),K2,R2,N2(mixed adversarial), guided one at a time.
Do not use any candidate1/old setup data or pretend these takes exist already.

Predeclare model: B cutoff 8 kHz -> log1p -> StandardScaler -> balanced LinearSVC
C=.001, no hyperparameter search. Two fixed complementary folds, one take per
class in training and the other in test, then swap. Fit scaler/model only on
each fold's training takes. Report each fold and pooled out-of-fold window
accuracy/confusion matrices, balanced accuracy, all class recalls, scratch->neutral
fraction, without gate and with gate. The quiet/adversarial difference between
the two neutral takes makes this a limited stress check, not robust validation.

Gate calibration uses the SEPARATE candidate2 acceptance quiet take
`8f3e07abc7344ab89b95827e99b1da16`, never the held-out pilot quiet take. Fixed
diagnostic gate active if RMS >0.146804% FS OR peak >0.579834% FS (quiet P95s).
Below gate output neutral. No smoothing, cooldown or gate search in this pilot.
This is offline diagnostic inference; do not change the live/default gate.

Operationalize A's 'rarely scratch->neutral' as <=5%, declared BEFORE recording.
For a conservative pilot PASS require >=90% mean two-fold accuracy and <=5%
scratch->neutral in both no-gate and gated results; show both fold results so
an aggregate cannot conceal failure. This only permits progression toward final
collection, not a claimed final classifier. Original durability check still
remains before final freeze/collection. If pilot fails, recommended hardware
option (b): compare a fully adhered paper surface, not gain first. That change
requires a new setup ID and fresh acceptance. Do not recommend (c) from these
four diagnostic takes, and do not start that surface test automatically.
