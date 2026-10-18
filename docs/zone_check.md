# Marked-zone check before immediate hardware freeze

Status: **awaiting A's board dimensions and original gain-A mark/photo**.
No new measurement has been performed or accepted under this protocol.

## Current decisions

- Sole hardware operator/performer: A. Goal: final data for B tonight/early tomorrow.
- Keep pickup and white bandage restraint mounted as-is; do not rub them.
- Restore original INST GAIN 2 position **A** using its mark/photo. If there is no
  reference, tell the assistant before turning; approximate old angle notes are not
  a verified original setting. Never claim A restored without confirmation.
- Windows input 100, audio enhancements OFF, +48V OFF. WASAPI USB Audio CODEC,
  stereo int16 ch2, 48000 Hz, capture block 480, FFT 2400 / 50 ms, features unchanged.
- All old data is pilot. C-labelled contact-rub runs are invalid for board-rub
  comparison. A/B rub locations are unverified. Final ranges require THIS check.
- Old 15 dB light-rub target is retired; light rub is characterized as a risk.

## First physical step (wait for the report before choosing coordinates)

A measures the board width x height x thickness, pickup-center distance from the
left/top edges, and describes the padding under the board. Photograph the full board
and the original gain mark if available. Use one consistent top-left board corner
as coordinate origin and keep that orientation. Do not move pickup or change gain
while locating the original reference. Do not invent distances from a close-up photo.

After A supplies actual dimensions, choose KNOCK and RUB outlines on bare board,
clear of the pickup, white mounting bandage and cable. Mark boundaries with narrow
tape outlines/marker; perform actions INSIDE the bare-board area, not on the tape.
Distances/sizes are pending board geometry. Gain, mounting and support stay fixed.

## Four short measurements after zones and gain are confirmed

Close FFT Trainer. Run `uv run device_check.py`; find WASAPI USB Audio CODEC index.
Replace 15 below if it changed. Each command opens stereo int16 at the unchanged
rate/block. There is 1 s warmup followed by 10 s measurement; new files isolate this
run set from historical calibration. Guide one condition, then wait for A's result.

```cmd
uv run device_check.py --device 15 --rate 48000 --channels 2 --seconds 10 --label zone_check_A_quiet --gain-note A_original --csv measurements/zone_check_intervals.csv --summary-csv measurements/zone_check_summary.csv
uv run device_check.py --device 15 --rate 48000 --channels 2 --seconds 10 --label zone_check_A_rub_light --gain-note A_original --csv measurements/zone_check_intervals.csv --summary-csv measurements/zone_check_summary.csv
uv run device_check.py --device 15 --rate 48000 --channels 2 --seconds 10 --label zone_check_A_rub_firm --gain-note A_original --csv measurements/zone_check_intervals.csv --summary-csv measurements/zone_check_summary.csv
uv run device_check.py --device 15 --rate 48000 --channels 2 --seconds 10 --label zone_check_A_knock_hard --gain-note A_original --csv measurements/zone_check_intervals.csv --summary-csv measurements/zone_check_summary.csv
```

- Quiet: hands off board/cable/interface for full run.
- Light rub: naturally light continuous fingertip rub INSIDE marked RUB zone.
- Firm rub: comfortable medium-to-firm continuous fingertip rub in SAME zone,
  no pauses, no pickup/bandage/cable contact. Start action before Enter.
- Hard knock: prepare hand, wait for MEASURING NOW, make **3 hardest intended
  comfortable knuckle knocks** INSIDE KNOCK zone. Do not strike pickup or use objects.
- Send SUMMARY/ch2 lines and hard-knock CLIP status. If missed action, retain and
  explicitly exclude the run, then retry under a new label.

## Acceptance and bounded contingency

Use median and P10 of 50 ms RMS, contrast = 20 log10(rub / matching quiet median).
Every measurement must be complete, no dropped blocks and zero digital clipping.
Firm-rub median contrast >=about **10 dB**, hard-knock max peak <=about **70% FS**,
and no CLIP flash permits immediate freeze/documentation. Record light-rub weakness;
do not require 15 dB or tune away the supplied constraints.

If failed, propose ONE most likely physical fix based on actual geometry/results
(e.g. move only the rub zone closer without contact), then repeat once. No feature
or sampling changes, no endless gain search. If still failed, report the failure
honestly with the best reproducible setup/risk rather than inventing acceptance.

Final frozen coordinates/photos/padding and measured quiet/light/firm/knock ranges
go into SETUP and HANDOFF before solo final collection. Give C a short participant
instruction: use only marked bare-board zones, demonstrate firm fingertip rubbing
in practice, never touch sensor or restraint. Formal trial performance remains untested.
