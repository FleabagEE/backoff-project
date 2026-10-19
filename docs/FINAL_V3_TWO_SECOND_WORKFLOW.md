# Current collection protocol: one action per two-second take

This latest operator request supersedes 25-second continuous/event-rhythm
collection and the incomplete pilot. Work on a-tuning; preserve model-training.
No old recordings are moved, renamed, relabelled, overwritten or deleted.
Wood-board hardware remains candidate2: thin bottom double-sided adhesive,
top retaining tape, gain A, bare wood nail scratch. Audio capture, 50ms FFT
and existing 1200-feature processing remain unchanged.

New root `data_sessions/final_v3` was absent and is created empty. Each GUI launch
creates a fresh uniquely named child session (timestamp + UUID) once input is
opened; it starts with zero takes, never loads or resumes an older session.
Settings/snapshot files are not recorded takes. Keep the same GUI open across
batches so all new recordings stay in one session. No pilot or diagnostic data
is imported. The full resolved child path is displayed before recording.

```cmd
uv run visualizer.py --final --session-root data_sessions/final_v3 --setup-id A_wood30x30x6_v3_candidate2 --scratch-surface wood --fast-takes
```

Defaults: Train workspace, recording kind take, split train, duration2s,
performer A. Select class and enter notes by hand. Notes must contain the class
as a word/token (underscore-separated is accepted); rub additionally needs
scratch_nail_wood. Examples: knock_medium_right_center,
rub_scratch_nail_wood_normal_right_index, neutral_quiet.

After editing notes, click the FFT plot once to leave text editing. Tap R to
record the next take using the current class/split/notes. Held R, repeated key
events, R during recording or R while editing fields do not launch extra takes.
Notes/variation persist after save; change only between batches. Record Data
button also works. Pending save failures are retried before starting a new take.

At start: silent visible READY countdown0.3s, then KNOCK ONCE / SCRATCH ONCE /
NEUTRAL ACTION. Perform exactly one action about0.3–0.5s after start, scratch for
about1s, then still until stop at2s (normal GUI scheduling may add a few ms).
Neutral = one described adversarial action, or remain still for quiet. No beeps
are emitted. Each completed take auto-saves a distinct atomic NPZ and updates
the take log and large per-class TRAIN/HOLDOUT counters. These are take counts,
not FFT-frame counts. Config/metadata identify single_action_2s separately from
the prior twelve-events/25s protocol.

Full preflight shows session path, selected class, kind, split, duration, notes
and performer. Wrong kind (including diagnostic), duration other than2s, missing
class/performer or class absent from notes warns and blocks starting. Unhealthy
audio also blocks. Holdout retains explicit confirmation for EACH take; the
0.3s cue begins only after confirmation. Early-stopped takes (<1.9s) are retained
as excluded, not counted as completed. No raw GUI training is allowed in this
mode; subsequent modelling must handle quiet context within each take offline.

About130 takes were mentioned, but new per-class batch quotas were not specified;
the fast-mode counters intentionally show counts without old25s quotas. Do not
invent a new quota or silently equate one2s take to a25s take. The earlier six-
take checkpoint/5-second quiet-prefix calibration cannot be reused unchanged
with2s takes. Re-specify the checkpoint and independent quiet calibration from
the new recordings before fitting/scoring; never use old pilot to fill gaps.

Verification uses real Dear PyGui widgets and synthetic arrays in temporary
sessions, with no hardware recordings: defaults/preflight, two consecutive R
takes with auto-stop/save and unchanged notes, held-key protection, text-edit
protection, warnings, holdout confirmation and excluded early stops.
