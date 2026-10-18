# Solo final collection: A

Frozen measured setup: 17 x 27 cm board directly on table, gain A restored from
mark/photo (operator confirmed), no hardware CLIP flash during hard-knock test.
RUB is ON separate bandage nearest pickup; KNOCK ON farther bandage. Never rub
pickup or its restraining bandage. Keep gain, bandages and cable placement fixed.
Windows input 100, enhancements OFF, +48V OFF. Existing capture/features unchanged.
Record full-board and gain photos under docs/setup/; record pickup/zone coordinates
and cable restraint before packing. No padding is installed. Direct table contact
is a portability risk: nearby table vibration and table changes need later checks.

## Launch and recording

Close old GUI and diagnostics. Run `uv run visualizer.py --final`.
This always creates a NEW session on first Record. Do not reopen mid-session just
to change notes. If interrupted, saved takes remain safe; record new session IDs
and hand all final sessions to B. Counters show the current launch only.

Confirm LIVE/ch2, rising FFT updates and response to intended actions before data.
Keep Performer A and Take limit 25 s. Select class, enter variation, keep split
train. Start knock/rub just before Record and continue until automatic stop.
Knock 2-3/s; rub continuously with finger pad, without striking sensor/cable.
Confirm Saved after EVERY take. If an action was missed/wrong, retain its file and
report take ID for explicit exclusion; do not silently label it valid.

## Training takes: 10 knock + 10 rub + 16 neutral

For rounds 1-6: knock -> rub -> neutral -> additional neutral. For rounds 7-10:
knock -> rub -> neutral. Each row gives the variation notes for that take.
Use only the fixed interaction patch; vary position within it, not on pickup.

| Round | knock | rub | neutral | additional neutral (rounds 1-6) |
|---|---|---|---|---|
| 1 | medium dominant center | firm fingertip slow lengthwise | quiet hands off 1 | palm slap |
| 2 | light dominant center | medium fingertip fast lengthwise | quiet hands off 2 | fingertip tap |
| 3 | hard dominant center | firm fingertip crosswise | quiet hands off 3 | fingertip flick |
| 4 | medium other hand | medium other hand lengthwise | typing nearby | place cup |
| 5 | light other hand | firm fingertip circles | place phone | lift cup/phone |
| 6 | hard other hand | medium fingertip reverse direction | drag object | palm leaning |
| 7 | medium patch left | firm finger pad slow | elbow leaning | -- |
| 8 | medium patch right | medium finger pad fast | nearby table taps | -- |
| 9 | light varying patch position | light fingertip continuous | talking | -- |
| 10 | hard varying patch position | light other hand continuous | rest hand/lift hand | -- |

At most two light rub takes. Keep adversarial actions safe for board/materials.
Variation notes and performer are saved automatically in takes.csv and NPZ.
Export after each few rounds. Do not train yet; B owns production model.

## Holdout LAST: two per class

After all 36 training takes, change Data split to holdout. Record knock, rub,
neutral, then knock, rub, neutral (25 s each). Use fresh comfortable variations,
including neutral adversarial actions. Enter descriptive notes. Never use these
six takes for fitting or threshold tuning. All export rows include split labels.

Press Export Dataset for B. Send session path / saved status for QA. Success means
42 valid takes, not just many correlated FFT rows. QA baseline is a sanity check,
not proof of stranger/bakeoff success.

## Two-minute restore / tester instructions

Restore same board orientation, direct support and fixed zones; inspect pickup
mounting and cable so they cannot rattle or drag. Restore photographed gain A.
Connect UM2 USB, verify input 100/enhancements OFF/+48V OFF and WASAPI USB CODEC
index (may change). Select stereo ch2 at frozen 48000 Hz. Briefly check quiet,
firm rub and hard knock levels against docs/zone_check_results.md before capture.
After a table change, repeat level check and a nearby-table disturbance check.

C can tell participants: "Use the marked farther patch for a knuckle knock. For
rub, keep your finger pad in contact and rub firmly back and forth on the nearer
patch. Practice once before the trial. Do not touch the red sensor or its fixing
bandage." Formal SPACE trial-set evaluation remains B's responsibility.
