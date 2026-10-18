# B: start with these corrected datasets

**Delivery:** NPZ files are distributed in the cloud ZIP, not this Git folder.
See root HANDOFF_B.md for the cloud-link placeholder and docs/cloud_archive.json
for archive size/hash. Code, metadata and QA remain on GitHub. Extract the ZIP
to obtain train.npz/holdout.npz at the paths documented below.

Source: data_sessions/20261017_195725_85cb47b5. All performer A, October 17, 2026
(America/Los_Angeles). Original takes are preserved byte-for-byte.

| File | Purpose | Takes | Rows x features |
|---|---|---:|---:|
| train.npz | fitting / grouped validation | 36: neutral 16, knock 10, rub 10 | 19095 x 1200 |
| holdout.npz | held-out evaluation only | 7: neutral 3, knock 2, rub 2 | 3732 x 1200 |

IMPORTANT: operator wrote holdout in notes but left GUI split=train. Seven
post-training takes were corrected ONLY in these derived exports, using the
explicit take-ID manifest docs/final_split_corrections.csv. Raw NPZ/takes.csv
still say train; never fit all raw rows indiscriminately. GUI's current training
buffer also contains the mislabeled holdout: do not click Train Model on it.
No model fit was requested in the capture workflow before this correction.

Use np.load(..., allow_pickle=False). X is the original full 1200 FFT amplitudes;
y indexes class_names. Each row has take_ids, split, elapsed_s, rms_fs, peak_fs.
takes_json records original_split and correction reason; config_json is the
unchanged capture configuration. Split at take level, never random windows.

## QA result: collected, not bakeoff-ready

Fixed sanity recipe log1p -> StandardScaler -> LinearSVC, GroupKFold by take,
all transforms fitted inside each fold. Grouped window accuracy 51.51%; held-out
window accuracy 70.18%. QA.md / qa_report.json contain matrices, class metrics,
fold IDs and per-take predicted sets. Every held-out take's raw prediction set
contained all three labels. These 25 s takes are NOT formal SPACE trials, but
the result exposes false-positive risk under set-based scoring. This QA baseline
has already evaluated the holdout; it is no longer an untouched future test if
used to iterate the recipe. B should use grouped training CV for development and
reserve fresh trials for final independent validation.

Quiet P95=0.2223% FS from training quiet takes; 10 of 12 rub takes (including
holdout) had median RMS below that reference. It is a descriptive flag, not a
reason to delete takes or set a high gate. Only two train rubs were explicitly
light; weak signal also occurred in medium/firm takes. Snapshot medians do not
prove sensor failure or action failure. B needs event/neutral handling, an
appropriately conservative gate and temporal decisions, then real trial tests.

One neutral drag take lasted 20.297 s (433 rows); retained alongside the 25 s
repeat. An extra 25 s neutral holdout was also retained. Max captured peaks in
two medium knocks reached 74.115% / 72.763% FS, above the calibration 70% goal;
neither number alone proves clipping. No raw PCM is saved, so analog waveform
clipping cannot be reconstructed from these summaries.

Frozen hardware: UM2 INST2, gain A restored from reference, +48V OFF; Windows
input100/enhancements OFF; WASAPI USB Audio CODEC (then index15), stereo int16
ch2, 48000 Hz / capture480 / FFT2400 samples50ms. Board17x27cm directly on table,
RUB on separate bandage nearest pickup, KNOCK on farther bandage. Pickup mounting
bandage untouched. Direct table contact, one person/table and missing measured
sensor/patch coordinates and setup photos limit portability/reproducibility.

No capture rate/block/FFT/feature processing changed for this review. The QA log
transform is offline baseline preprocessing only, not a change to recorded data.
Existing 20 Hz frequency-axis offset after DC removal and cadence-dependent
smoothing (~21 FFT updates/s) remain B review items. Optional <16kHz/log features
belong to B and require matched inference processing; do not silently alter data.

Reproduce into a NEW directory (outputs are never overwritten):

```cmd
uv run qa_dataset.py data_sessions/20261017_195725_85cb47b5 --overrides docs/final_split_corrections.csv --output handoff/reproduced_review
```

take_audit.csv lists per-take variation, levels, quiet-like fraction and SHA256
of each original take. No model artifact is exported; production training and
SPACE trial-set recorder remain B's responsibility.
