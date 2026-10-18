# Zone-check results

> HISTORICAL INTERACTION: current label rub now means fingernail scratch on paper. Old fingertip rub data is superseded for training; preserve it as history. Follow docs/scratch_v2.md (or ../docs/scratch_v2.md from docs) and HANDOFF_B.md for v2.

Board: 17 x 27 cm. A clarified that actions occur ON two separate bandages:
nearest pickup=RUB, farther=KNOCK. Keep the pickup's mounting bandage untouched.
This supersedes the bare-board proposal, without revalidating historical C runs.

All runs: 10 s, 200 nonoverlapping 50 ms RMS windows, complete=True,
overflow_blocks=0, digital clipping=0. Requested gain: original A, using its
available mark/photo. A subsequently confirmed restoration and no hardware CLIP
flash. Board rests directly on the table, without padding.

| zone_check_A_ suffix | ch2 median RMS (% FS) | P10 RMS (% FS) | max peak (% FS) |
|---|---:|---:|---:|
| quiet | 0.1174 | 0.1139 | 0.674 |
| rub_light | 0.2622 | 0.1761 | 1.645 |
| rub_firm | 0.8005 | 0.3892 | 7.431 |
| knock_hard | 0.3010 | 0.1428 | 58.868 |

20 log10(RMS / quiet median): light median 6.98 dB, P10 3.52 dB;
firm median 16.67 dB, P10 10.41 dB. These are level contrasts, not classifier
accuracy or signal-only SNR. Digital criteria pass (firm >=about 10 dB,
hard peak <=about 70% FS). Keep measured gain/mounting unchanged.

Remaining documentation: pickup/zone coordinates, cable strain relief and setup
photos. Direct table contact is a cross-table portability risk. Demonstrate firm
fingertip rub; light rub remains weak and must inform B's energy gate.
No final/holdout collection or classifier QA is established by these diagnostics.

Raw results retained in measurements/zone_check_intervals.csv and
measurements/zone_check_summary.csv. Sampling, FFT and features unchanged.
