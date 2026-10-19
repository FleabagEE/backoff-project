# Frozen hardware setup and data collection

## Current v3 candidate: new wooden board (October 19)

This section supersedes ALL historical setup/data-selection text below.
Current re-test setup ID: `A_wood30x30x6_v3_candidate2`. A confirms thin
double-sided tape underneath the pickup and retaining tape over the top. This is the
single permitted acceptance re-test, followed by durability if levels pass.
LATEST OPERATOR COLLECTION DECISION: A now explicitly starts full final_v3 with
an early checkpoint after six event-style takes, despite the level-only FAIL
below. Keep this candidate2 hardware unchanged. Do not finish/reuse pilot_wood.
Only the new final_v3 source folder is eligible. Use --event-rhythm: actions at
1,3,...23s (12/25s), not continuous positive actions. See FINAL_V3_EVENT_PROTOCOL
in docs for gate/segmentation and pause/decision rules. Durability is not measured.

Candidate2 initial acceptance re-test is now FAIL: normal median 0.22467% FS
(target about >=0.3%); light P10 0.13705% FS below quiet P95 0.14680% FS;
hard-knock peak 14.86206% FS (headroom passes). Durability was not started.
The single mounting correction/re-test allowance is exhausted. The revised
operator plan above authorizes collection with an early checkpoint; it does
not change these measured results or establish final bakeoff readiness.
Candidate1 mounting details below remain historical; candidate2 uses the
thin double-sided bottom adhesive and top restraint confirmed above.

Candidate1 initial GUI acceptance FAILED: normal scratch median 0.13355% FS,
light P10 0.11655% FS below quiet P95 0.11789% FS. Hard-knock peak 8.30383% FS;
hardware CLIP lamp did not flash. See STATUS_FOR_CLAUDE.md for actual take IDs.
One contact/mounting correction is proposed, not yet performed. If confirmed,
record it as candidate2 and re-test once. Candidate1 is not an accepted setup.

- Board: 30 x 30 cm, 6 mm thick; wood construction/species unknown.
- Pickup: ordinary tape at bottom AND top, operator reports full contact.
  Tape product/thickness unknown; do not assume the previously proposed adhesive.
- Pickup center: left/top distances each described as opened-hand thumb-to-middle-
  finger span. Exact cm coordinates remain pending; never guess. Photos to be
  added by A in `docs/setup/`.
- No separate cable strain relief. Board directly on table, no padding.
- Knock and scratch zones each approximately 5 cm from pickup; exact centers and
  boundaries pending. Do not contact pickup, mounting tape or cable during actions.
- No paper pad. A explicitly confirms fingernail EDGE back-and-forth scratching
  on bare wood, NOT fingertip-skin rubbing. Label remains `rub`, notes tag
  `scratch_nail_wood`. Knock = knuckle knock in knock zone.
- Unchanged: gain A, Windows input100/enhancements OFF/+48V OFF; WASAPI USB Audio
  CODEC stereo ch2, 48 kHz, 480-frame capture block, 2400-sample/50 ms FFT and
  original 1200-feature processing.
- ALL previous pilot/final/final_v2/diagnostic sessions are different setups:
  preserve originals but exclude ALL from v3 training AND evaluation. Acceptance
  diagnostics also never enter formal training or evaluation.

Acceptance: GUI diagnostic quiet 10s, normal wood scratch 10s, light scratch 10s,
three hardest knocks. Paper comparison omitted because A chose bare wood/no pad.
Target normal scratch median about >=0.3% FS, light P10 clearly above quiet P95,
knock peak about <70% FS, no clipping. Then leave board for 10 minutes, lift/set
down once, knock 20 times; repeat quiet/normal scratch. Scratch median must not
drop more than about 2 dB. If failed, one most-likely fix and one re-test, with
changed configuration documented as a new candidate ID. No results exist yet.

## Historical setups below: excluded from v3 training and evaluation

**CURRENT INTERACTION 2 (supersedes all fingertip-rub instructions below):**
`rub` now means fingernail scratch on the four-edge-taped printer-paper pad.
Keep gain A and all capture/FFT processing unchanged. See
[scratch v2 setup and pending dimensions/photos](docs/scratch_v2.md).
Old rub data is superseded, raw files preserved. Knock/neutral remain selected.

**FREEZE CONFIRMED BY A:** original gain A restored; hardware CLIP did not flash;
board directly on table, no padding. Keep this measured configuration unchanged.
Follow [solo final collection](docs/solo_collection.md) with `uv run visualizer.py --final`.
Photos, pickup/zone coordinates and cable restraint details remain to document.

**LATEST UPDATE:** board 17 x 27 cm; RUB is ON the separate bandage nearest the
pickup, KNOCK ON the farther bandage, superseding the bare-board proposal below.
Keep the pickup restraint untouched. Zone checks pass digital criteria: firm-rub
median contrast 16.67 dB, hard peak 58.868% FS, zero digital clipping/overflow.
Keep measured gain/mounting fixed. See `docs/zone_check_results.md`.

Bakeoff: **Thursday, October 22, 2026**. A owns hardware/data collection; B owns
model training, energy gate, temporal decisions and trial recorder; C owns slides.
Software collection workflow is ready. Hardware is a **candidate configuration**
until gain photos, board dimensions, sensor coordinates and pad details are filled.

**Current decision (supersedes historical calibration notes):** A collects ALL data
solo. The latest written instructions confirm C rubs contacted the red pickup /
its white mounting bandage, not the board. C is **INVALID for board-rub comparison**;
all files remain preserved with companion exclusions. KEEP the mounting bandage.

The arbitrary 15 dB light-rub target is **retired**. Select **original gain A**, not
the raised B gain, subject to A restoring its real photo/tape mark (not yet confirmed).
Historical A had light-rub median/P10 contrasts 10.19/5.09 dB and hard-knock peak
22.97% FS; B did not improve the median contrast and raised the tested peak to 47.09%.
A/B rubbing locations may also have been near/on the pickup, so these are exploratory
references, not final level ranges. All existing collection data is PILOT ONLY.

Next define marked RUB and KNOCK zones on **bare board**, separated from pickup and
bandage, using A's actual board dimensions. Run the short [zone check](docs/zone_check.md)
at restored A gain: quiet/light rub/firm rub 10 s each and 3 hardest board knocks.
Freeze if firm-rub median contrast >=about 10 dB and hard peak <=about 70% FS,
no clipping. Otherwise make ONE likely physical fix and repeat once. Never change
capture/FFT/feature processing. Final ranges, coordinates, padding and photos remain
pending; no final/holdout collection yet. Demonstrate firm fingertip board rub to
testers and retain light-rub risk for B's gate instead of chasing another gain goal.

## Start here (Windows cmd)

Close older FFT Trainer windows and diagnostic scripts, then run from this repo:

```cmd
uv run visualizer.py
```

If uv is not on PATH:

```cmd
"%USERPROFILE%\.local\bin\uv.exe" run visualizer.py
```

The app prefers **USB Audio CODEC / Windows WASAPI**, currently PyAudio index 15.
Device entries show index and host API, so duplicate names are distinguishable.
Select the verified WASAPI endpoint. Indices can change after reconnecting USB.
If the entry is absent, reconnect UM2 and restart; do not select a laptop microphone.
Failed inputs produce an explicit error and cannot record dummy spectra.

Expected status: `LIVE`, channel 2, FFT update counter continuing to rise. Knock
on the board and rub the marked area; PCM/FFT readings should react. Display
Auto-scale adjusts only the graph, not feature values or training/inference.
Capture is **PyAudio, stereo int16 -> second channel, 48000 Hz**. No backend,
rate or channel fallback is allowed for this profile.

## Collect a take

1. Classes `neutral`, `knock`, `rub` already exist. Remain in **Train** mode.
2. Enter **Performer** (A/B/C) and **Variation / notes** (force, position, action).
3. Leave **Take limit** at 25 s (allowed 5-60 s); click the class's **Select**.
4. For knock/rub, start the action BEFORE pressing **Record Data**. Knock steadily
   2-3 times/s, or rub continuously, with minimal silent gaps.
5. Click **Record Data**. It auto-stops at the limit; **Stop Recording** ends early.
   Keep acting until recording stops. Confirm a `Saved take_....npz` message.
6. Rotate **knock -> rub -> neutral -> neutral**; update notes before each take.
7. Click **Export Dataset for B** after a batch, and before handing over files.

The class counter counts newly acquired FFT vectors, not physical gestures.
The live counter does not repeatedly save cached features. Recording pauses on
stale/stopped audio; takes with detected capture problems are archived as excluded.
A save error retains the take in memory and shows **Retry Save**: resolve the disk
problem and retry BEFORE closing. Startup transient frames are excluded by warmup.

Every stopped take is independently saved. A normal exit also stops/saves the active
partial take and exports valid saved takes. An interrupted process can lose the
currently active take, but earlier saved takes remain. At most a 25 s take is normally
at risk; never rely solely on an in-memory class counter.

**Clear data** excludes all saved takes of that class in the CURRENT session and
resets its count. Originals become `*.excluded.npz`; they are not deleted. A later
export omits them. Do not clear a class merely to begin its next take. Wrong-label
take? Stop immediately; log its filename and ask B to exclude it, or clear/recollect
that class if few takes exist. Manually excluded filenames must contain `.excluded.`.

Each launch starts a NEW session folder. The GUI does not reload prior takes.
B can train from multiple compatible session exports. Reopening the GUI does not
erase older sessions. There is deliberately no SPACE trial recorder in this change;
SPACE/trial sets and slide actions remain B/C's work.

## Files to give B

Each session is under `data_sessions/YYYYMMDD_HHMMSS_id/`:

- `config.json`: device/API/channel/rate, FFT, library versions and source hashes.
- `SETUP_snapshot.md`: copy of this hardware setup when session began.
- `take_*.npz`: original feature snapshots, per-frame elapsed time, RMS/peak and take notes.
- `takes.csv`: automatically generated take log, including performer, variation,
  duration, frame count, validity and filename.
- `dataset.npz`: aggregate created by **Export Dataset for B** or normal exit.

Give B the **entire session folder**, this repo's capture code and `HANDOFF_B.md`.
Do not hand over just a `.model` or the manually created `take_log.csv` template.
Audio WAV is NOT saved: these archives hold FFT features and level measurements.
Changing feature extraction later may require recollection; B can change preprocessing
and models using saved features. Back up session folders after each collection batch.

Recovery/re-export without opening the GUI:

```cmd
uv run collection.py "data_sessions\YOUR_SESSION_FOLDER"
```

## Frozen signal path (keep these unchanged during collection)

| Item | Current configuration |
|---|---|
| Laptop | ASUS Vivobook, Windows |
| Interface | Behringer U-PHORIA UM2, same USB port/cable |
| Pickup cable / input | Passive contact pickup -> 1/4-inch TS instrument cable -> **INST 2** |
| Phantom power | **+48 V OFF** |
| Device | USB Audio CODEC, **Windows WASAPI**, currently index 15 |
| Channels | Capture 2; select **ch2** before mono FFT buffer |
| PCM / rate / block | int16 scale, **48000 Hz**, **480 frames per channel/block** |
| FFT | Existing **50 ms / 2400 samples**; same Hamming, rFFT, weighting and smoothing |
| Model features | Full spectrum: **1200 amplitudes**, not the 512 auxiliary grouped bins |
| Feature cadence | Target 30 updates/s, actual timestamps saved; latest overlapping windows |
| Windows input level | **100**, unmuted |
| Audio enhancements | **OFF**; this resolved severely suppressed signal |
| INST GAIN 2 | Current calibrated position above minimum; A: add tape mark/photo |
| Other knobs | A: photograph GAIN 1, OUTPUT and DIRECT MONITOR settings |
| Board | Hard portable board; A: record material/dimensions/orientation |
| Sensor mount | Flat against hard board, tape across housing; A: photo, exact tape/contact details |
| Sensor position | A: x/y in mm from marked board corner |
| Interaction zones | A: mark knock/rub zone outlines and distance from sensor |
| Cable strain relief | A: tape to board separately with short relaxed loop |
| Board pads | A: record material, size, thickness, count and locations; validate on two tables |

Current code intentionally fixes the ESTABLISHED 48000 Hz and 50 ms settings;
model algorithms and `preprocess_data()` are unchanged. Do not adjust Windows
volume to make the FFT plot taller. Do not train with an older mono capture profile.

## Measured hardware reference (October 17)

The earlier PyAudio mono starter captured only noise although sounddevice mono
included INST 2. PyAudio stereo proved the signal resides on channel 2. This is
now fixed in capture. The prior callback scheduling was also replaced by a continuous
main render loop. Signal values below were measured before the software repair,
using the same physical ch2, sample rate and gain. FFT feature sampling cadence is
now recorded explicitly; recollect final training data with the repaired app.

| Condition / take | Measurement |
|---|---|
| Settled quiet, mounted | ch2 RMS approximately **0.114% FS** |
| Normal knocks, `mount_check` | interval RMS **0.390-0.692% FS**, peaks **7.336-12.256% FS** |
| Rub, `mount_check`, late segment | interval RMS **0.160-0.543% FS**, median **0.315% FS** |
| Rub vs quiet | about **8.8 dB** higher RMS in those segments; variable, not a classifier guarantee |
| Strong knock, `hard_knock_mounted_final` | max peak **32.135% FS**, overall RMS **1.4086% FS**, no clipping/overflow |
| PyAudio stereo routing confirmation | ch2 max peak **22.485% FS**; ch1 remained near noise |

These were not a fully controlled force study. Labelled light/medium/hard knock
and light/hard rub reference takes still need recording at the finalized setup.
SIG can remain dark during measurable short signals; do not raise gain just to
light it. CLIP remaining off does not prove analog linearity, and digital endpoint
clip%=0 alone does not exclude earlier analog saturation.

## Calibration / mounting procedure

Use `uv run device_check.py` to list input indices/APIs. With the GUI CLOSED:

```cmd
uv run device_check.py --device 15 --rate 48000 --channels 2 --seconds 15 --label silence --csv measurements/calibration.csv
```

Repeat separately with labels `knock_light`, `knock_medium`, `knock_hard`,
`rub_light`, `rub_hard`, performing each named action throughout its own take.
Evaluate ch2. Record knob position and Windows input level along with measurements.
For knocks compare MAX peak, since RMS includes gaps. For continuous rub compare
median interval RMS against quiet at the same gain/mount.

- Set Windows volume/processing first; then change only INST GAIN 2 if necessary.
- Hardest expected knock: target <=80% FS, zero clipping, no CLIP indication or
  audible distortion. Current 32.135% gives useful margin; don't chase a larger plot.
- A light-rub RMS 10 dB above quiet is a useful starting calibration target, NOT a
  bakeoff requirement. Actual spectral separation must be validated by B.
- If clipping occurs before rub is clear, improve contact/position/strain relief;
  gain alone cannot fix poor input signal-to-noise ratio. Revalidate all classes
  after any change. Use a separate CSV filename for each gain candidate.

Mount the sensor flat and firmly using its supplied adhesive or a thin, firm,
repeatable contact layer appropriate to its casing. Avoid thick soft foam BETWEEN
sensor and board. Tape can provide gentle downward restraint without crushing the
pickup. Fix cable separately so it cannot pull up the sensor or scrape the board.
Start with the pickup about 5 cm from the interaction zone; test all zone corners,
mark its final position, and transport the board without remounting.

Put identical rubber/neoprene or dense foam pads near the board corners (5-10 mm
thickness is a starting point). No rocking, no table contact under the sensor, and
no cable pulling against the table. Test on two tables before freezing pad layout.
A passive piezo benefits from an instrument input's high impedance: excessive
loading can alter its spectrum. Keep INST 2 now that it has been verified.

## Three-person collection session: 80 minutes

| Minutes | Work |
|---|---|
| 0-15 | Restore setup, verify quiet/rub/strong knock, take photos and fill TBDs |
| 15-20 | Practice shared gestures; decide zones; test one take/export |
| 20-55 | Collect 48 short takes, rotating performers and labels |
| 55-65 | B trains initial model and energy gate using exported features |
| 65-80 | Fresh trial evaluation; inspect failures; collect targeted additions |

Target **12 knock + 12 rub + 24 neutral**, each about 25 s. For each of A/B/C,
perform four cycles of **knock -> rub -> neutral -> neutral**. A maintains hardware,
B handles notes/model, C cues/times actions; rotate controls when A performs.
Vary person, force, zone position and rub direction. Use continuous gestures to
reduce mislabeled quiet frames; B must still handle low-energy gaps in knock data.

Each person's eight neutral takes cover: quiet/talking; palm slaps; fingertip taps;
typing nearby; placing a cup/phone; dragging an object; leaning/pressing; mixed table
bumps/cable disturbances. Keep adversarial actions active for much of their take.
Neutral gets the MOST time. Cross-target negatives matter: rub must not emit knock,
and knock must not emit rub.

B should validate on held-out **people/takes**, never randomly split adjacent windows.
Rehearse 5 positive + 5 negative trials per target. Knock positive passes only with
`{knock}` or `{neutral, knock}`; rub analogous. Target negatives require the target
absent. A stray frame fails a trial. GUI output, trial sets and slide events must use
the same finalized label after gate/smoothing, consistent with course rules.

## Two-minute pre-demo checklist

- **0:00-0:30:** Same board/pads/USB port; check sensor/cable tape, knob marks,
  phantom OFF. Confirm no rocking.
- **0:30-1:00:** Windows level 100, enhancements OFF; compare quiet/rub/strong knocks
  with the reference using the script. Close script before opening GUI.
- **1:00-1:30:** Launch GUI, verified WASAPI endpoint, LIVE counter rising, ch2 response;
  load B's model matching this capture profile.
- **1:30-2:00:** Neutral/knock/rub and next/previous slide smoke test; verify B's SPACE
  trial start/stop clears and prints sets, then reset slides. That recorder is still
  B/C's implementation work, not part of this collection-only change.

If references fail, restore the documented configuration. Do not change gain or
routing silently after training. Photograph final knobs/mounting/Windows settings
and place those images alongside this file before final collection.
